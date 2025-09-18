import * as yaml from 'js-yaml';

/**
 * Parse a YAML file and return its content as a formatted text string
 * @param file - The File object to parse
 * @returns Promise<string> - The parsed YAML content as formatted text
 */
export const parseYamlFile = async (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (event) => {
      try {
        const yamlContent = event.target?.result as string;
        
        if (!yamlContent) {
          reject(new Error('File is empty or could not be read'));
          return;
        }

        // Parse the YAML content
        const parsedData = yaml.load(yamlContent);
        
        // Convert the parsed data back to a formatted string
        const formattedYaml = yaml.dump(parsedData, {
          indent: 2,
          lineWidth: -1, // No line wrapping
          noRefs: true,
          sortKeys: false
        });
        
        resolve(formattedYaml);
      } catch (error) {
        reject(new Error(`Failed to parse YAML: ${error instanceof Error ? error.message : 'Unknown error'}`));
      }
    };
    
    reader.onerror = () => {
      reject(new Error('Failed to read file'));
    };
    
    reader.readAsText(file);
  });
};
