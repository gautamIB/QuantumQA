import json
import logging
import base64
import re

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from playwright.async_api import Page, ElementHandle
from openai import AsyncOpenAI
from ..core.models import Coordinates

logger = logging.getLogger(__name__)


async def find_and_click_most_relevant_element(
        user_goal: str,
        button_text: str = None,
        target: str = None,
        normalized_targets: List[str] = None,
        page: Page = None,
        all_dom_elements: List[Dict[str, Any]] = None,
        openai_client: AsyncOpenAI = None) -> Optional[Coordinates]:
    """
    Analyzes the current page, finds the most relevant element based on the user's goal.
    Returns the coordinates of the element for clicking.
    
    Args:
        user_goal: The goal or instruction from the user
        button_text: Optional text of the button to find
        target: Optional target element description
        normalized_targets: Optional list of normalized target descriptions
        page: The Playwright Page object
        all_dom_elements: Optional list of all DOM elements
        openai_client: Optional AsyncOpenAI client
        
    Returns:
        Coordinates of the element if found, None otherwise
    """
    if page is None:
        logger.error("Page object not available")
        return None

    # lowercase the button_text and convert to unique words
    button_text_words = []
    if target:
        button_text_words.append(target.lower().strip())
    button_text_words.extend(
        button_text.lower().split(',') if button_text else [])
    button_text = ', '.join(list(dict.fromkeys(button_text_words))).strip()
    print(f"Final Button text: {button_text}")

    # Wait for target elements to be visible before proceeding
    logger.info(
        f"Waiting for elements matching target: '{target}' / button_text: '{button_text}'"
    )

    try:
        print(f"Finding most relevant element for goal: '{user_goal}'")
        # button_text = button_text.lower() if button_text else target.lower()
        # 1. Extract all clickable elements using Playwright's API
        # This includes buttons, links, and elements with an onclick attribute
        elements_to_evaluate = []

        # Define selectors for clickable elements
        clickable_selectors = [
            'a', 'button', 'input[type="button"]', 'input[type="submit"]',
            '[role="button"]', '[role="link"]', '[role="menuitem"]',
            '[role="tab"]', '[onclick]', '[data-action]', '[data-target]',
            '[class*="btn"]', '[class*="button"]'
        ]

        # Combine selectors for a single query
        combined_selector = ', '.join(clickable_selectors)

        # Get all potentially clickable elements
        elements = await page.query_selector_all(combined_selector)

        print(f"Found {len(elements)} potential clickable elements in DOM")

        # Process each element
        for idx, element in enumerate(elements):
            try:
                # Enhanced visibility check with timeout
                try:
                    # Check if element is visible with a timeout
                    is_visible = await element.is_visible()

                    # Additional check for elements that might be technically visible but not interactive
                    if is_visible:
                        # Check if element is not hidden by CSS or has zero dimensions
                        is_actually_visible = await element.evaluate("""
                            (el) => {
                                const style = window.getComputedStyle(el);
                                const rect = el.getBoundingClientRect();
                                
                                return style.display !== 'none' && 
                                       style.visibility !== 'hidden' && 
                                       style.opacity !== '0' &&
                                       rect.width > 0 && 
                                       rect.height > 0 &&
                                       !el.hasAttribute('disabled');
                            }
                        """)
                        is_visible = is_visible and is_actually_visible
                except Exception as e:
                    logger.warning(
                        f"Error checking visibility for element {idx}: {e}")
                    is_visible = False

                if is_visible:
                    # Get element properties
                    tag_name = await element.evaluate(
                        'el => el.tagName.toLowerCase()')
                    text = await element.text_content() or ""
                    text = text.strip()

                    # Get element attributes
                    attributes = {}
                    for attr in [
                            'id', 'class', 'role', 'name', 'type', 'value',
                            'href', 'onclick', 'data-action', 'data-target',
                            'aria-label'
                    ]:
                        attr_value = await element.get_attribute(attr)
                        if attr_value:
                            attributes[attr] = attr_value

                    # Get element classes
                    classes = attributes.get(
                        'class',
                        '').split() if attributes.get('class') else []

                    # Get HTML
                    html = await element.evaluate('el => el.outerHTML')

                    # Add check to ensure at least one word from the button_text is in the text or attributes
                    should_add = True  # Default to True if no button_text is provided
                    if button_text:
                        # Only filter if button_text is provided
                        button_words = button_text.lower().split(',')
                        text_match = any(word in text.lower()
                                         for word in button_words)

                        # Check in attribute values
                        attr_values_match = any(
                            word in str(value).lower()
                            for value in attributes.values()
                            for word in button_words)

                        # Check in attribute keys
                        attr_keys_match = any(word in str(key).lower()
                                              for key in attributes.keys()
                                              for word in button_words)

                        # Only apply filtering if button_text is provided
                        should_add = text_match or attr_values_match or attr_keys_match
                    if should_add:
                        print(
                            f"PRESENT:: Element {idx}, element text: {text}, element class: {classes}. "
                        )

                        if attributes.get('role') == 'tab' and text.lower(
                        ).strip() == 'create':
                            #skip the element
                            print(
                                f"SKIPPING:: Element {idx}, element text: {text}, element attributes: {attributes} "
                            )
                            continue

                        elements_to_evaluate.append({
                            "index": idx,
                            "text": text,
                            "html": html,
                            "tag": tag_name,
                            "attributes": attributes,
                            "classes": classes,
                            "element":
                            element  # Store the actual element handle
                        })
                    else:
                        # print(
                        #     f"SKIPPED: Element {idx}, element text: {text}, element attributes: {attributes}"
                        # )
                        pass

            except Exception as e:
                logger.warning(f"Error processing element {idx}: {str(e)}")

        print(f"Evaluating {len(elements_to_evaluate)} clickable elements")

        for elem in elements_to_evaluate:
            if elem['text'] != '':
              print(f"Element: {elem['index']}, {elem['text']}, {elem['tag']}")

        # Prepare the data for the LLM
        element_data = []
        for elem in elements_to_evaluate:
            # Create a simplified representation for the LLM
            element_data.append({
                "index": elem["index"],
                "text": elem["text"],
                "tag": elem["tag"],
                "attributes": {
                    k: v
                    for k, v in elem["attributes"].items() if k in [
                        "id", "data-target", "data-action", "data-content",
                        "href", "role", "aria-label", "title"
                    ]
                }
            })

        # Create a prompt for the LLM
        prompt = f"""
        
Your task is to act as a highly specialized web automation agent. 
Your sole purpose is to analyze a list of clickable web elements and, based on a given user goal, select the single most relevant element to click.

## Instructions:

1.  **Analyze the Goal**: Carefully read the user's objective to understand the intent behind the click.

2.  **Examine Elements**: Analyze the provided JSON list of clickable elements. Pay close attention to their `role`, `text`, `id`, and other attributes.

3.  **Prioritize Clicks**: Prioritize elements as follows, with higher numbers being more important:

    * **Priority 1**: Elements that have text or attributes that directly match keywords in the user's goal (e.g., "Add to Cart," "Sign Up," "Download").

    * **Priority 2**: Buttons or links (`<button>`, `<a>`, `[role="button"]`) over other interactive elements (`[role="tab"]`, `<div>`).

    * **Special Rule**: For "create" or "add" type of user goal, prioritize `role="button"` over `role="tab"` to avoid selecting a tab for a click action.

4.  **Deduce and Select**: Based on your analysis and priorities, determine the index of the single most relevant element. If no element is a clear match, select the element that is the most logical choice for the user's next step.

5.  **Provide Justification**: Provide a clear, step-by-step reasoning for your choice. Explain why you selected the chosen element and why you discarded others.

6.  **Assess Confidence**: Assign a confidence score between 0.0 and 1.0. A score of 1.0 means you are certain of the choice. A score below 0.5 indicates high uncertainty and a need for further information.

## Input:

User Goal: "{user_goal}"

Clickable Elements:

{json.dumps(element_data, indent=2)}

## Output:
You **must** return a single JSON object. The object must follow this exact structure, with no extra text or explanations outside the JSON.

```json

{{

    "selected_index": <integer index of the selected element>,

    "reasoning": "<string explanation of why this element was selected>",

    "confidence": <float number between 0.0 and 1.0>

}}
        """

        # Call the OpenAI API directly if client is provided
        if openai_client:
            system_message = "You are a helpful assistant that analyzes web elements to find the most relevant one for a given goal."
            response = await openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use an appropriate model
                messages=[{
                    "role": "system",
                    "content": system_message
                }, {
                    "role": "user",
                    "content": prompt
                }],
                temperature=0.1,
                max_tokens=500)
            completion = response.choices[0].message.content
        else:
            # Fallback to traditional approach if no client provided
            logger.error("No OpenAI client provided, cannot analyze elements")
            return None

        # Parse the LLM response
        try:
            # Helper function to extract JSON from response
            def extract_json_from_text(text):
                # Find JSON-like structure using regex
                json_match = re.search(r'\{[\s\S]*\}', text)
                if json_match:
                    json_str = json_match.group(0)
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Try to clean up the JSON string
                        # Replace single quotes with double quotes
                        json_str = json_str.replace("'", '"')
                        try:
                            return json.loads(json_str)
                        except json.JSONDecodeError:
                            return None
                return None

            # Extract JSON from completion
            llm_result = extract_json_from_text(completion)
            if not llm_result:
                logger.error(
                    f"Failed to extract JSON from response: {completion}")
                return None

            selected_index = llm_result.get("selected_index")
            reasoning = llm_result.get("reasoning", "No reasoning provided")
            confidence = llm_result.get("confidence", 0)

            print(
                f"LLM selected element index {selected_index} with confidence {confidence}"
            )
            print(f"Reasoning: {reasoning}")

            # Find the selected element in our original list
            selected_element = None
            for elem in elements_to_evaluate:
                if elem["index"] == selected_index:
                    selected_element = elem
                    break

            if selected_element:
                # Get the element from the evaluated elements
                element = selected_element.get("element")

                if not element:
                    # If we have a custom selector generator, try using it to generate selectors for this element
                    if custom_selector_generator and selected_element["text"]:
                        # Create an action plan dictionary similar to what _generate_smart_selectors expects
                        action_plan = {
                            "action": "click",
                            "user_goal": user_goal
                        }
                        if button_text:
                            action_plan["target"] = button_text
                        else:
                            action_plan["target"] = selected_element["text"]

                        # Generate smart selectors for the target text
                        target_text = selected_element["text"]
                        selectors = custom_selector_generator(
                            target_text, action_plan)

                        # Try each selector
                        for selector_info in selectors:
                            try:
                                selector = selector_info["selector"]
                                strategy = selector_info["strategy"]

                                # Use Playwright to find the element with the selector
                                element = await page.query_selector(selector)

                                if element:
                                    print(
                                        f"Found element using selector: {selector} with strategy: {strategy}"
                                    )
                                    break
                            except Exception as selector_error:
                                logger.warning(
                                    f"Error using selector {selector}: {str(selector_error)}"
                                )

                    # If we still don't have an element, return None
                    if not element:
                        logger.error(
                            f"Could not retrieve element with index {selected_index}"
                        )
                        return None

                # Get element text for logging
                element_text = selected_element["text"]

                print(
                    f"Clicking element: '{element_text}', attributes: {selected_element['attributes']}"
                )

                # Get element coordinates
                bounding_box = await element.bounding_box()
                if bounding_box:
                    center_x = int(bounding_box['x'] +
                                   bounding_box['width'] / 2)
                    center_y = int(bounding_box['y'] +
                                   bounding_box['height'] / 2)

                    # Create coordinates object
                    coords = Coordinates(x=center_x, y=center_y)

                    # Log the coordinates
                    print(
                        f"Found element at coordinates: ({center_x}, {center_y})"
                    )

                    return coords
                else:
                    logger.error("Could not get bounding box for element")
                    return None
            else:
                error_msg = f"Selected element index {selected_index} not found in the list of elements"
                logger.error(error_msg)
                return None
        except Exception as e:
            error_msg = f"Error parsing LLM response: {str(e)}"
            logger.error(error_msg)
            logger.error(
                f"Response content: {completion if 'completion' in locals() else 'No response'}"
            )
            return None

    except Exception as e:
        error_msg = f"Failed to find and click relevant element: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())

        return NoneI
