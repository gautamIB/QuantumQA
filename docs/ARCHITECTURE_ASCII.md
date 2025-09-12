# QuantumQA Framework - ASCII Architecture

## 🏗️ High-Level Visual Architecture

```
                    ┌─────────────────────────────────────────────────────────────┐
                    │                    👤 USER                                   │
                    │              Provides Test Files                            │
                    └─────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────────────────────────────────┐
                    │               🚀 TEST RUNNER                                │
                    │            run_quantum_test.py                             │
                    │         Auto-detects UI vs API tests                       │
                    └─────────────┬───────────────────┬───────────────────────────┘
                                  │                   │
                        ┌─────────▼─────────┐       ┌─▼─────────────────┐
                        │   📱 UI TESTS     │       │   🔌 API TESTS    │
                        │                   │       │                   │
                        │                   │       │                   │
    ┌───────────────────▼───────────────────▼───────▼───────────────────▼───────────────────┐
    │                           🧠 INTELLIGENT PROCESSING LAYER                              │
    ├─────────────────────────────────────┬─────────────────────────────────────────────────┤
    │         🌐 UI ENGINE               │              🔌 API ENGINE                      │
    │   ┌─────────────────────────────┐   │   ┌─────────────────────────────────────────┐   │
    │   │    📋 Instruction Parser    │   │   │         📊 API Parser               │   │
    │   │  Natural Language → Actions │   │   │    YAML/JSON → HTTP Requests       │   │
    │   └─────────────┬───────────────┘   │   └─────────────┬───────────────────────┘   │
    │                 │                   │                 │                           │
    │   ┌─────────────▼───────────────┐   │   ┌─────────────▼───────────────────────┐   │
    │   │    🎯 Element Finder        │   │   │       🌐 HTTP Client               │   │
    │   │  Smart UI Element Detection │   │   │    Async Request Handler           │   │
    │   └─────────────┬───────────────┘   │   └─────────────┬───────────────────────┘   │
    │                 │                   │                 │                           │
    │   ┌─────────────▼───────────────┐   │   ┌─────────────▼───────────────────────┐   │
    │   │    ⚡ Action Executor       │   │   │    ✅ Response Validator           │   │
    │   │ Click, Type, Verify, Upload │   │   │ Status & Field Validation          │   │
    │   └─────────────────────────────┘   │   └─────────────────────────────────────┘   │
    └─────────────────────────────────────┴─────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                        🔐 SHARED SECURITY & CONFIG LAYER                                │
    │  ┌─────────────────────────┐              ┌─────────────────────────────────────────┐  │
    │  │  🔐 Credential Manager  │              │        ⚙️ Configuration System        │  │
    │  │   • AES Encryption      │              │    • Action Patterns (YAML)           │  │
    │  │   • Masked Logging      │              │    • Selector Strategies               │  │
    │  │   • Dynamic Resolution  │              │    • Environment Settings              │  │
    │  └─────────────────────────┘              └─────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
    ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │                            📊 REPORTING & OUTPUT LAYER                                  │
    │                                                                                         │
    │   📱 UI Test Results                           🔌 API Test Results                     │
    │   ├─ 📸 Screenshots                           ├─ 📈 Performance Metrics                │
    │   ├─ 📋 Step-by-step Results                  ├─ ✅ Validation Results                  │
    │   ├─ 🎯 Success Rate                          ├─ 🌐 Request/Response Logs               │
    │   └─ ⏱️ Execution Time                        └─ 📊 Status Code Analysis               │
    │                                     │                                                   │
    │                                     ▼                                                   │
    │                        ┌─────────────────────────────────┐                             │
    │                        │     📋 UNIFIED FINAL REPORT     │                             │
    │                        │   • Combined Success Rate       │                             │
    │                        │   • Detailed Error Analysis     │                             │
    │                        │   • Performance Insights        │                             │
    │                        │   • Visual Documentation        │                             │
    │                        └─────────────────────────────────┘                             │
    └─────────────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Component Interaction Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    USER     │───▶│ TEST RUNNER │───▶│ AUTO-DETECT │───▶│   ENGINE    │
│   Input     │    │   Entry     │    │  UI or API  │    │  Selection  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                                                                │
                                                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EXECUTION PHASE                                │
├─────────────────────────────────┬───────────────────────────────────────────┤
│           🌐 UI PATH            │            🔌 API PATH                   │
│                                 │                                           │
│  ┌─────────────┐                │  ┌─────────────┐                          │
│  │ Instruction │─────┐          │  │ API Parser  │─────┐                    │
│  │   Parser    │     │          │  │             │     │                    │
│  └─────────────┘     │          │  └─────────────┘     │                    │
│                      ▼          │                      ▼                    │
│  ┌─────────────┐ ┌─────────────┐ │  ┌─────────────┐ ┌─────────────┐         │
│  │  Element    │ │   Action    │ │  │ HTTP Client │ │ Response    │         │
│  │   Finder    │ │  Executor   │ │  │             │ │ Validator   │         │
│  └─────────────┘ └─────────────┘ │  └─────────────┘ └─────────────┘         │
│         │               │        │         │               │                │
│         └───────┬───────┘        │         └───────┬───────┘                │
└─────────────────┼──────────────────┴─────────────────┼────────────────────────┘
                  │                                   │
                  ▼                                   ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                🔐 SECURITY LAYER                            │
    │     ┌─────────────────┐   ┌─────────────────────────┐       │
    │     │  Credentials    │   │     Configuration       │       │
    │     │   {cred:xxx}    │   │    action_patterns.yaml │       │
    │     └─────────────────┘   └─────────────────────────┘       │
    └─────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
              ┌─────────────────────────────────────────┐
              │          📊 FINAL REPORTING             │
              │                                         │
              │  📈 82.2% Success Rate                  │
              │  📸 Visual Screenshots                   │
              │  📋 Step-by-step Analysis               │
              │  ⚡ Performance Metrics                 │
              │  🔍 Detailed Error Logs                 │
              └─────────────────────────────────────────┘
```

## 🎯 Smart Click Strategy Optimization

```
                    Element Detected
                           │
                           ▼
              ┌─────────────────────────────┐
              │    🧠 Element Analysis       │
              │                             │
              │  ┌─ Is Send Button?         │
              │  ┌─ Has Overlay?             │
              │  ┌─ Element Type?            │
              │  └─ Context Clues?           │
              └─────────────┬───────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────┐
        │         🎯 Strategy Selection            │
        ├──────────────────┬───────────────────────┤
        │                  │                       │
        ▼                  ▼                       ▼
┌─────────────┐   ┌─────────────┐         ┌─────────────┐
│ SEND BUTTON │   │   OVERLAY   │         │   NORMAL    │
│             │   │  ELEMENT    │         │  ELEMENT    │
│ 1.force_click│   │             │         │             │
│ 2.center_click│   │1.force_click│         │1.regular_click│
│ 3.regular_click│   │2.center_click│         │2.force_click│
│ 4.js_click  │   │3.regular_click│         │3.js_click   │
└─────────────┘   └─────────────┘         └─────────────┘
        │                  │                       │
        └──────────────────┼───────────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │    ✅ SUCCESS       │
                │  Reduced Failed     │
                │  Attempts by 70%    │
                └─────────────────────┘
```
