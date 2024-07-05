"""Script to generate Requirements Document in parts usign LLM and then combining them to create a complete requirements_document."""

import os
from dotenv import load_dotenv
from langchain.schema.runnable import RunnablePassthrough
from langchain_openai import ChatOpenAI

from prompts.architect import ArchitectPrompts

load_dotenv()

def create_full_document(result):
    """
    Create a full Markdown document from the SequentialChain results.
    """
    document = f"""
# Project Requirements Document

{result['project_overview']}

{result['architecture']}

{result['folder_structure']}

{result['microservice_design']}

{result['tasks']}

{result['standards']}

{result['implementation_details']}

{result['license']}
        """
    return document

def write_to_file(content, filename='requirements.md'):
    """
    Write the content to a file.
    """
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)


if __name__=="__main__":
    # Get Architect Prompts
    architect_prompts = ArchitectPrompts()

    # Initialize your LLM
    llm = ChatOpenAI(model="gpt-4o-2024-05-13", temperature=0.3, max_retries=5, streaming=True, seed=4000, top_p=0.4)

    # Ensure each chain has the correct input_variables and output_key
    project_overview_chain = architect_prompts.PROJECT_OVERVIEW_PROMPT | llm | (lambda x: x.content)  # This step extracts only the content part from the llm output AImessage
    
    architecture_chain = architect_prompts.ARCHITECTURE_PROMPT | llm | (lambda x: x.content)

    folder_structure_chain = architect_prompts.FOLDER_STRUCTURE_PROMPT | llm | (lambda x: x.content)

    microservice_design_chain = architect_prompts.MICROSERVICE_DESIGN_PROMPT | llm | (lambda x: x.content)

    tasks_breakdown_chain = architect_prompts.TASKS_BREAKDOWN_PROMPT | llm | (lambda x: x.content)

    standards_chain = architect_prompts.STANDARDS_PROMPT | llm | (lambda x: x.content)

    implementation_details_chain = architect_prompts.IMPLEMENTATION_DETAILS_PROMPT | llm | (lambda x: x.content)

    license_legal_chain = architect_prompts.LICENSE_DETAILS_PROMPT | llm | (lambda x: x.content)

    overall_chain = (
        RunnablePassthrough.assign(project_overview=project_overview_chain)
        | RunnablePassthrough.assign(architecture=architecture_chain)
        | RunnablePassthrough.assign(folder_structure=folder_structure_chain)
        | RunnablePassthrough.assign(microservice_design=microservice_design_chain)
        | RunnablePassthrough.assign(tasks=tasks_breakdown_chain)
        | RunnablePassthrough.assign(standards=standards_chain)
        | RunnablePassthrough.assign(implementation_details=implementation_details_chain)
        | RunnablePassthrough.assign(license=license_legal_chain)
    )

    # Run the chain
    req_document_in_parts = overall_chain.invoke(input={
        "user_request": 'I want to develop a Title Requests Micro-service adhering to MISMO v3.6 standards to handle get_title service using GET REST API Call in .NET?',
        "task_description": 'This task is part of Project Initiation Phase and has two deliverables, a project requirements document and a list of project deliverables.\n\n            Do not assume anything and request for additional information if provided information is not sufficient to complete the task or something is missing.',
        "additional_information": 'To develop a Title Requests Micro-service adhering to MISMO v3.6 standards to handle the `get_title` service using a GET REST API call in .NET, you can follow these steps:\n\n1. **Define the Data Models**: Based on the provided XML schema definitions, you need to create corresponding C# classes. You can use tools like xsd.exe to generate C# classes from the XSD files.\n\n2. **Create the .NET Project**: Start by creating a new ASP.NET Core Web API project.\n\n3. **Implement the Data Models**: Use the generated C# classes from the XSD files. These classes will represent the data structures defined in the MISMO v3.6 schema.\n\n4. **Create the Controller**: Implement a controller to handle the GET request for the `get_title` service.\n\n5. **Service Layer**: Implement a service layer to handle the business logic for fetching the title information.\n\n6. **Configure Dependency Injection**: Set up dependency injection for the service layer in the `Startup.cs` file.\n\nHere is a basic example to get you started:\n\n### Step 1: Generate C# Classes from XSD\nUse the `xsd.exe` tool to generate C# classes from the XSD files. For example:\n```sh\nxsd.exe /c /n:YourNamespace /out:Models TITLE_REQUEST.xsd\n```\n\n### Step 2: Create the .NET Project\nCreate a new ASP.NET Core Web API project:\n```sh\ndotnet new webapi -n TitleRequestService\ncd TitleRequestService\n```\n\n### Step 3: Implement the Data Models\nPlace the generated C# classes in the `Models` folder of your project.\n\n### Step 4: Create the Controller\nCreate a new controller named `TitleRequestController`:\n```csharp\nusing Microsoft.AspNetCore.Mvc;\nusing TitleRequestService.Models;\n\nnamespace TitleRequestService.Controllers\n{\n    [ApiController]\n    [Route("api/[controller]")]\n    public class TitleRequestController : ControllerBase\n    {\n        private readonly ITitleRequestService _titleRequestService;\n\n        public TitleRequestController(ITitleRequestService titleRequestService)\n        {\n            _titleRequestService = titleRequestService;\n        }\n\n        [HttpGet("{id}")]\n        public ActionResult<TITLE_REQUEST> GetTitleRequest(string id)\n        {\n            var titleRequest = _titleRequestService.GetTitleRequestById(id);\n            if (titleRequest == null)\n            {\n                return NotFound();\n            }\n            return Ok(titleRequest);\n        }\n    }\n}\n```\n\n### Step 5: Service Layer\nCreate a service interface and implementation:\n```csharp\nusing TitleRequestService.Models;\n\nnamespace TitleRequestService.Services\n{\n    public interface ITitleRequestService\n    {\n        TITLE_REQUEST GetTitleRequestById(string id);\n    }\n\n    public class TitleRequestService : ITitleRequestService\n    {\n        public TITLE_REQUEST GetTitleRequestById(string id)\n        {\n            // Implement the logic to fetch the title request by ID\n            // This could be from a database, an external API, etc.\n            return new TITLE_REQUEST\n            {\n                // Populate the TITLE_REQUEST object\n            };\n        }\n    }\n}\n```\n\n### Step 6: Configure Dependency Injection\nConfigure the service in `Startup.cs`:\n```csharp\npublic void ConfigureServices(IServiceCollection services)\n{\n    services.AddControllers();\n    services.AddScoped<ITitleRequestService, TitleRequestService>();\n}\n```\n\n### Step 7: Run the Application\nRun the application and test the GET endpoint:\n```sh\ndotnet run\n```\n\nYou can now make a GET request to `http://localhost:5000/api/titlerequest/{id}` to fetch the title request information.\n\nThis is a basic outline to get you started. You will need to implement the actual logic for fetching and processing the title request data according to your specific requirements and the MISMO v3.6 standards.\nQuestion: What specific standards or regulations are relevant to developing a Title Requests Micro-service adhering to MISMO v3.6 standards?\nInitial Answer: The specific standards or regulations relevant to developing a Title Requests Micro-service adhering to MISMO v3.6 standards are the MISMO v3.6 XML Schema definitions. These schemas define the structure and data types for various elements involved in title requests, such as `TITLE_REQUEST_EXTENSION`, `TITLE_REQUEST_DETAIL_EXTENSION`, `TITLE_COMMITMENT_EXTENSION`, and others. These schemas ensure that the data exchanged between systems is consistent and adheres to the standards set by MISMO.\n\nTo develop a Title Requests Micro-service that adheres to MISMO v3.6 standards, you would need to:\n\n1. **Understand the MISMO v3.6 XML Schema**: Familiarize yourself with the complex types and elements defined in the MISMO v3.6 schema files. These schemas define the structure of the XML documents that your micro-service will produce and consume.\n\n2. **Implement Schema Validation**: Ensure that the XML documents your micro-service handles are validated against the MISMO v3.6 schemas. This can be done using XML validation libraries available in your programming language of choice.\n\n3. **Adhere to Data Types and Structures**: Follow the data types and structures defined in the MISMO v3.6 schemas for elements like `TITLE_REQUEST_EXTENSION`, `TITLE_REQUEST_DETAIL_EXTENSION`, etc. This ensures that the data conforms to the expected format.\n\n4. **Use Appropriate Namespaces**: The schemas use specific namespaces (e.g., `http://www.mismo.org/residential/2009/schemas`). Ensure that your XML documents use these namespaces correctly.\n\n5. **Handle Extensions Appropriately**: The schemas include various extension points (e.g., `TITLE_REQUEST_EXTENSION`, `TITLE_COMMITMENT_EXTENSION`). Make sure your micro-service can handle these extensions as defined in the schema.\n\nBy adhering to these standards and using the provided schema definitions, you can ensure that your Title Requests Micro-service is compliant with MISMO v3.6 standards.\nFollow-up Question: Are there any industry-specific regulations or compliance requirements, in addition to the MISMO v3.6 XML Schema, that need to be considered when developing a Title Requests Micro-service?\nFollow-up Answer: I don\'t have any additional information about the question.\n\n',
        "license_text": "Property of XYZ COMPANY"
    })

    # Create the full document
    full_document = create_full_document(req_document_in_parts)

    # Write the document to a file
    write_to_file(full_document)

    print(f"Requirements document has been written to {os.path.abspath('./requirements.md')}")
