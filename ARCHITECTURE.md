# Architecture Documentation

This document provides detailed architecture diagrams for the Azure Analysis Services MCP Agent solution.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Local Environment"
        User[👤 User]
        Agent[AI Agent<br/>simple_agent.py<br/>Python]
        MCP[MCP Server<br/>server.py<br/>Python]
    end
    
    subgraph "Azure Cloud"
        subgraph "Azure Function App"
            Func[Azure Function<br/>QueryAasFunction.cs<br/>.NET 8]
            MI[Managed Identity<br/>OAuth Token]
        end
        
        subgraph "Azure Analysis Services"
            AAS[(AAS Server<br/>Tabular Model<br/>Adventure Works)]
        end
        
        subgraph "Azure AI Services"
            OpenAI[Azure OpenAI<br/>GPT-4]
        end
    end
    
    User -->|1. Natural language query| Agent
    Agent -->|2. OpenAI API| OpenAI
    OpenAI -->|3. DAX query suggestion| Agent
    Agent -->|4. MCP Protocol<br/>stdio| MCP
    MCP -->|5. HTTPS POST<br/>JSON payload| Func
    Func -->|6. Request OAuth token| MI
    MI -->|7. Azure AD token| Func
    Func -->|8. ADOMD.NET<br/>asazure:// protocol| AAS
    AAS -->|9. Query results| Func
    Func -->|10. JSON response| MCP
    MCP -->|11. Query results| Agent
    Agent -->|12. Formatted answer| User
    
    style User fill:#e1f5ff,color:#000
    style Agent fill:#fff4e1,color:#000
    style MCP fill:#fff4e1,color:#000
    style Func fill:#e1ffe1,color:#000
    style MI fill:#ffe1e1,color:#000
    style AAS fill:#e1e1ff,color:#000
    style OpenAI fill:#ffe1f5,color:#000
```

---

## 2. Authentication Flow (Managed Identity)

```mermaid
sequenceDiagram
    participant Func as Azure Function
    participant MI as Managed Identity
    participant AAD as Azure AD
    participant AAS as Analysis Services
    
    Note over Func: Function App starts
    Func->>MI: Get managed identity token
    MI->>AAD: Request token for<br/>https://*.asazure.windows.net
    AAD->>MI: Return OAuth 2.0 token
    MI->>Func: Token acquired
    
    Note over Func: Query request received
    Func->>Func: Build connection string<br/>with token
    Func->>AAS: Connect via ADOMD.NET<br/>+ OAuth token
    AAS->>AAS: Validate token<br/>Check role permissions
    AAS-->>Func: Connection established
    Func->>AAS: Execute DAX/MDX query
    AAS-->>Func: Query results
    Func-->>Func: Format as JSON
    
    Note over Func,AAS: Token cached for reuse<br/>Refreshed automatically
```

---

## 3. Request/Response Data Flow

```mermaid
flowchart LR
    subgraph "Input"
        A[User Question:<br/>'How many customers?']
    end
    
    subgraph "AI Agent Processing"
        B[OpenAI GPT-4]
        C[Generate DAX:<br/>EVALUATE<br/>COUNTROWS Customer]
    end
    
    subgraph "MCP Layer"
        D[MCP Server<br/>server.py]
        E[Tool: query_analysis_services]
    end
    
    subgraph "Azure Function"
        F[Validate Request]
        G[Acquire Token]
        H[Execute Query]
    end
    
    subgraph "Data Source"
        I[(Azure Analysis<br/>Services)]
    end
    
    subgraph "Response Path"
        J[Raw Results]
        K[JSON Format]
        L[Natural Language<br/>Answer]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    E -->|HTTP POST| F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    K --> D
    D --> B
    B --> L
    
    style A fill:#e1f5ff,color:#000
    style C fill:#fff4e1,color:#000
    style E fill:#ffe1e1,color:#000
    style I fill:#e1e1ff,color:#000
    style L fill:#e1ffe1,color:#000
```

---

## 4. Component Interaction (Sequence Diagram)

```mermaid
sequenceDiagram
    actor User
    participant Agent as AI Agent<br/>(simple_agent.py)
    participant OpenAI as Azure OpenAI
    participant MCP as MCP Server<br/>(server.py)
    participant Func as Azure Function<br/>(.NET 8)
    participant AAS as Azure Analysis<br/>Services
    
    User->>Agent: "Show top 5 customers"
    
    Agent->>OpenAI: System prompt +<br/>user question
    OpenAI->>Agent: Suggested DAX query
    
    Agent->>MCP: Call tool:<br/>query_analysis_services
    activate MCP
    
    MCP->>MCP: Load environment:<br/>AZURE_FUNCTION_URL
    
    MCP->>Func: POST /api/query<br/>{"query": "EVALUATE..."}
    activate Func
    
    Func->>Func: Validate JSON payload
    Func->>Func: Acquire OAuth token<br/>(Managed Identity)
    
    Func->>AAS: ADOMD Connection +<br/>Execute query
    activate AAS
    AAS-->>Func: DataTable results
    deactivate AAS
    
    Func->>Func: Convert to JSON
    Func-->>MCP: {"rows": [...]}
    deactivate Func
    
    MCP-->>Agent: Return results
    deactivate MCP
    
    Agent->>OpenAI: Format results as<br/>natural language
    OpenAI-->>Agent: Formatted answer
    
    Agent-->>User: "Here are the top 5 customers:<br/>1. Contoso ($1.2M)<br/>2. Fabrikam ($980K)..."
```

---

## 5. Deployment Architecture

```mermaid
graph TB
    subgraph "Azure Subscription"
        subgraph "Resource Group"
            Storage[Storage Account<br/>Azure Files]
            
            subgraph "Function App"
                Runtime[.NET 8 Runtime<br/>Isolated Worker]
                Code[Function Code<br/>QueryAasFunction.cs]
                Settings[App Settings<br/>Environment Variables]
            end
            
            Identity[Managed Identity<br/>System-assigned]
        end
        
        AAS[Azure Analysis Services<br/>Tabular Model]
        AAD[Azure Active Directory<br/>Token Provider]
        Monitor[Application Insights<br/>Logging & Monitoring]
    end
    
    Developer[👨‍�💻 Developer]
    Client[💻 Client Machine<br/>MCP Server + Agent]
    
    Developer -->|Deploy via<br/>func CLI| Code
    Code --> Runtime
    Runtime --> Settings
    Runtime --> Identity
    
    Settings -.->|Read config| Runtime
    Identity -->|Request token| AAD
    AAD -->|OAuth token| Identity
    
    Client -->|HTTPS| Runtime
    Runtime -->|ADOMD.NET<br/>+ Token| AAS
    
    Runtime -->|Telemetry| Monitor
    Code -->|Store artifacts| Storage
    
    style Storage fill:#e1f5ff,color:#000
    style Runtime fill:#ffe1e1,color:#000
    style Code fill:#fff4e1,color:#000
    style Identity fill:#e1ffe1,color:#000
    style AAS fill:#e1e1ff,color:#000
    style AAD fill:#ffe1f5,color:#000
```

---

## 6. Protocol Stack

```mermaid
graph LR
    subgraph "Client Layer"
        A1[Python]
        A2[stdio]
        A3[MCP Protocol]
    end
    
    subgraph "Transport Layer"
        B1[HTTPS]
        B2[TLS 1.2+]
        B3[JSON Payload]
    end
    
    subgraph "Function Layer"
        C1[HTTP Trigger]
        C2[.NET 8 Runtime]
        C3[ADOMD.NET]
    end
    
    subgraph "Authentication"
        D1[Managed Identity]
        D2[OAuth 2.0]
        D3[JWT Token]
    end
    
    subgraph "Data Layer"
        E1[asazure:// protocol]
        E2[TDS Protocol]
        E3[Tabular Model]
    end
    
    A1 --> A2
    A2 --> A3
    A3 --> B1
    B1 --> B2
    B2 --> B3
    B3 --> C1
    C1 --> C2
    C2 --> D1
    D1 --> D2
    D2 --> D3
    C2 --> C3
    C3 --> E1
    E1 --> E2
    E2 --> E3
    
    style A3 fill:#fff4e1,color:#000
    style B3 fill:#e1f5ff,color:#000
    style C3 fill:#e1ffe1,color:#000
    style D2 fill:#ffe1e1,color:#000
    style E3 fill:#e1e1ff,color:#000
```

---

## 7. Why This Architecture?

```mermaid
graph TD
    Problem[Problem: Query Azure<br/>Analysis Services<br/>from AI Agent]
    
    Challenge1[Challenge 1:<br/>AAS requires ADOMD.NET]
    Challenge2[Challenge 2:<br/>Python has no ADOMD library]
    Challenge3[Challenge 3:<br/>XMLA over HTTP not supported]
    
    Solution1[✅ Solution:<br/>C# Azure Function<br/>with ADOMD.NET]
    
    Solution2[✅ Solution:<br/>Python MCP Server<br/>calls HTTP endpoint]
    
    Benefit1[Benefit:<br/>Secure OAuth<br/>authentication]
    Benefit2[Benefit:<br/>Managed Identity<br/>no secrets!]
    Benefit3[Benefit:<br/>Serverless<br/>auto-scaling]
    
    Problem --> Challenge1
    Problem --> Challenge2
    Problem --> Challenge3
    
    Challenge1 --> Solution1
    Challenge2 --> Solution2
    Challenge3 --> Solution1
    
    Solution1 --> Benefit1
    Solution1 --> Benefit2
    Solution1 --> Benefit3
    
    style Problem fill:#ffe1e1,color:#000
    style Challenge1 fill:#fff4e1,color:#000
    style Challenge2 fill:#fff4e1,color:#000
    style Challenge3 fill:#fff4e1,color:#000
    style Solution1 fill:#e1ffe1,color:#000
    style Solution2 fill:#e1ffe1,color:#000
    style Benefit1 fill:#e1f5ff,color:#000
    style Benefit2 fill:#e1f5ff,color:#000
    style Benefit3 fill:#e1f5ff,color:#000
```

---

## 8. Security Architecture

```mermaid
graph TB
    subgraph "Security Layers"
        L1[Layer 1: Network Security]
        L2[Layer 2: Identity & Access]
        L3[Layer 3: Data Protection]
        L4[Layer 4: Monitoring]
    end
    
    subgraph "Layer 1 Controls"
        N1[HTTPS Only]
        N2[Azure Firewall]
        N3[Private Endpoints<br/>optional]
    end
    
    subgraph "Layer 2 Controls"
        I1[Managed Identity]
        I2[Azure AD RBAC]
        I3[AAS Role Membership]
        I4[No Hardcoded Secrets]
    end
    
    subgraph "Layer 3 Controls"
        D1[Data Encrypted<br/>in Transit]
        D2[Data Encrypted<br/>at Rest]
        D3[TLS 1.2+]
    end
    
    subgraph "Layer 4 Controls"
        M1[Application Insights]
        M2[Audit Logs]
        M3[Query Monitoring]
    end
    
    L1 --> N1 & N2 & N3
    L2 --> I1 & I2 & I3 & I4
    L3 --> D1 & D2 & D3
    L4 --> M1 & M2 & M3
    
    style L1 fill:#ffe1e1,color:#000
    style L2 fill:#fff4e1,color:#000
    style L3 fill:#e1f5ff,color:#000
    style L4 fill:#e1ffe1,color:#000
    style I1 fill:#e1e1ff,color:#000
    style I4 fill:#e1e1ff,color:#000
```

---

## Key Design Decisions

### 1. **Hybrid Language Architecture**
- **C# for Azure Function**: Only language with ADOMD.NET support for AAS
- **Python for MCP/Agent**: Better for AI/ML ecosystem and MCP protocol

### 2. **Managed Identity (Recommended)**
- ✅ No secrets to manage or rotate
- ✅ Automatic token refresh
- ✅ Least-privilege access
- ✅ Azure AD integration

### 3. **Serverless with Azure Functions**
- ✅ Pay-per-execution pricing
- ✅ Auto-scaling based on load
- ✅ Built-in monitoring
- ✅ No infrastructure management

### 4. **MCP Protocol for AI Integration**
- ✅ Standard protocol for AI tools
- ✅ Language-agnostic
- ✅ Easy to integrate with various AI frameworks
- ✅ Clean separation of concerns

---

## Environment Variables Flow

```mermaid
graph LR
    subgraph "MCP Server .env"
        E1[AZURE_FUNCTION_URL]
        E2[AZURE_OPENAI_API_KEY]
        E3[AZURE_OPENAI_ENDPOINT]
    end
    
    subgraph "Azure Function App Settings"
        A1[AAS_REGION_HOST]
        A2[AAS_SERVER_NAME]
        A3[AAS_DATABASE]
        A4[USE_MANAGED_IDENTITY]
    end
    
    subgraph "MCP Server"
        M1[server.py]
        M2[simple_agent.py]
    end
    
    subgraph "Azure Function"
        F1[QueryAasFunction.cs]
    end
    
    E1 --> M1
    E2 --> M2
    E3 --> M2
    
    A1 --> F1
    A2 --> F1
    A3 --> F1
    A4 --> F1
    
    M1 -->|HTTP| F1
    
    style E1 fill:#fff4e1,color:#000
    style E2 fill:#e1f5ff,color:#000
    style E3 fill:#e1f5ff,color:#000
    style A4 fill:#e1ffe1,color:#000
```

**Note:** MCP Server only needs Azure Function URL - it doesn't need AAS credentials!

---

## Troubleshooting Flow

```mermaid
graph TD
    Start[Query fails]
    
    Q1{Status code?}
    
    E401[401 Unauthorized]
    E404[404 Not Found]
    E500[500 Server Error]
    E200[200 but empty]
    
    Fix1[Check Managed Identity<br/>enabled on Function App]
    Fix2[Verify AAS role membership]
    Fix3[Check Function URL<br/>in .env file]
    Fix4[Verify Function deployed]
    Fix5[Check Function logs]
    Fix6[Test AAS connectivity]
    Fix7[Validate DAX syntax]
    Fix8[Check AAS model<br/>has data]
    
    Start --> Q1
    Q1 -->|401| E401
    Q1 -->|404| E404
    Q1 -->|500| E500
    Q1 -->|200| E200
    
    E401 --> Fix1
    Fix1 --> Fix2
    
    E404 --> Fix3
    Fix3 --> Fix4
    
    E500 --> Fix5
    Fix5 --> Fix6
    
    E200 --> Fix7
    Fix7 --> Fix8
    
    style E401 fill:#ffe1e1,color:#000
    style E404 fill:#ffe1e1,color:#000
    style E500 fill:#ffe1e1,color:#000
    style Fix1 fill:#e1ffe1,color:#000
    style Fix2 fill:#e1ffe1,color:#000
```

---

## Future Enhancements

```mermaid
graph LR
    Current[Current State:<br/>Manual Setup]
    
    Phase2[Phase 2:<br/>Infrastructure as Code]
    Phase3[Phase 3:<br/>Enhanced Features]
    Phase4[Phase 4:<br/>Enterprise Scale]
    
    T1[Terraform/Bicep<br/>deployment]
    T2[CI/CD Pipeline]
    
    F1[Query caching]
    F2[Rate limiting]
    F3[Multi-model support]
    
    S1[Multi-region<br/>deployment]
    S2[High availability]
    S3[Disaster recovery]
    
    Current --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    
    Phase2 --> T1 & T2
    Phase3 --> F1 & F2 & F3
    Phase4 --> S1 & S2 & S3
    
    style Current fill:#e1f5ff,color:#000
    style Phase2 fill:#fff4e1,color:#000
    style Phase3 fill:#e1ffe1,color:#000
    style Phase4 fill:#ffe1f5,color:#000
```

---

## How to View These Diagrams

### In GitHub
All diagrams render automatically when you view this file on GitHub.

### In VS Code
1. Install "Markdown Preview Mermaid Support" extension
2. Open this file and press `Ctrl+Shift+V` (or `Cmd+Shift+V` on macOS)

### Export to PNG/SVG
1. Visit [Mermaid Live Editor](https://mermaid.live/)
2. Copy any diagram code
3. Export as PNG or SVG

### In Documentation Sites
Most static site generators (Hugo, Jekyll, Docusaurus) support Mermaid natively.
