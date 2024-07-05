"""
This module contains all the prompt templates for the Architect agent.

Each prompt in this module is designed to guide the Architect agent in 
performing its tasks. The prompts cover a wide range of scenarios, from 
analyzing user input and creating comprehensive requirements documents, to 
breaking down projects into independent tasks and enforcing best practices in
microservice architecture, project folder structure, and clean-code development.

The prompts are used to instruct the Architect agent on how to respond to user 
inputs and how to structure its outputs. They are essential for ensuring that 
the Architect agent can effectively assist users in implementing their projects.
"""

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate

from langchain.output_parsers import PydanticOutputParser


from models.architect import TasksList
from models.architect import QueryResult
from models.architect import RequirementsDoc

class ArchitectPrompts:
    """
    ArchitectPrompts class contains templates for guiding the Architect agent in its tasks.
    
    It includes templates for initial project requirements generation and for providing additional 
    information during project implementation. These templates ensure that the Architect agent can 
    effectively assist users in implementing their projects, adhering to best practices in 
    microservice architecture, project folder structure, and clean-code development.
    """

    INITIAL_TEMPLATE: str ="""Given the user request, supervisor expectation, and additional information about the project
    user request:"{user_request}"\n
    supervisor_expects: "{task_description}"\n
    additional_information: "{additional_information}"\n
    
    As a Solution Architect, you are responsible for implementing this assigned task. Your 
    duties include conducting a comprehensive analysis of the user request and the additional information to create a detailed 
    document necessary for the completion of the project.
    
    It is paramount that you break down the project into "descriptive technical deliverables" that other team_members can work on. 
    Each task should be self-contained and provide sufficient "technical details" for the team members who will undertake it.

    Mandate the utilization of microservice architecture, adhere to the best practice methods 
    for project folder structure, 12-factor application standards, domain-driven microservice 
    application design, clean-code development architecture standards, and code commenting 
    standards throughout the project.
    
    In addition, you should enforce programming language-specific standards. These standards vary depending 
    on the language used, but they generally include conventions for naming, commenting, indentation, and 
    organization of code.

    The final project should encompass all the source files, configuration files, unit test files, 
    OpenAPI specification file for the project in YAML format, dependency package manager files, 
    Dockerfile, .dockerignore, and a .gitignore file.

    I want you to adhere to all the requriements mentioned above. The document should be structured in a well
    formated markdown format. Follow the below example while generating the requirements document.
    "
    # Requirements Document
    . <description>
    .
    ## Table of Contents
    . <content>
    .
    ## Project OVerview
    . <description>
    .
    ## Architecture
    . <description>
    .
    ## Folder Structure
    .
    .
    ## Microservice Design
    .
    .
    ## Tasks
    .
    .
    ## Standards
    ### 12-Factor Application Standards
    .
    .
    ### Clean Code Standards
    .
    .
    ### Code Commenting Standards
    .
    . 
    ### Programming Language Specific Standards
    .
    .
    ### User Requested Standards
    .
    .
    ## License
    .
    .
    "

    Error messages will only be present if there is an issue with your previous response. 
    "{error_message}"

    Output format instructions:
    "{format_instructions}"
    """

    ADDITIONAL_INFO_TEMPLATE: str = """
    As a Solution Architect, you are responsible for implementing a given project. You have 
    previously prepared the requirements documents, tasks, and other necessary details for 
    your team members to complete the project.

    A team member has reached out to you requesting additional information to complete their 
    task. Please assist them.

    Error messages will only be present if there is an issue with your previous response. 
    "{error_message}"

    "{format_instructions}"

    Previously Prepared Requirements Documents:
    "{requirements_document}"

    Current Task Team is Working On:
    {current_task}

    Question:
    {question}
    """

    TASK_SEPARATION_TEMPLATE: str = """
    You have previously generated a well-formatted requirements document in markdown 
    format. Here is the generated requirements document:

    {requirements_document}

    The tasks suggested by you are as follows:
    {tasks}

    Below is an example of how the tasks should be formatted from the source:

    [
        "**Project Setup**
            - Initialize the project structure.
            - Set up version control with Git.
            - Create `.gitignore` and `.dockerignore` files.",

        "**Database Configuration**
            - Set up MySQL database.
            - Create database connection module.", 

        "**API Endpoints**
            - Create FastAPI application.
            - Implement CRUD operations for User resource.",
        .
        .
        .
        .
        "Task N"
    ]

    Your task is to convert the tasks from this markdown document into a list or an array. 
    Each task should be copied exactly as it appears in the markdown document and transformed 
    into an item in the list or array. No modifications should be made to the statements.

    Error messages will only be present if there is an issue with your previous response. 
    "{error_message}"

    "{format_instructions}"
    """

    PROJECT_OVERVIEW_PROMPT = PromptTemplate(
        template=""" Given the user request: "{user_request}"
            Supervisor expectations: "{task_description}"
            Additional information: "{additional_information}"

            As a Solution Architect, provide a comprehensive project overview. Include:
            1. A brief description of the project's purpose and goals
            2. The main features or functionalities to be implemented
            3. What schema definition models are needed to implement this service.

            Format your response in markdown, starting with a "## Project Overview" heading.""",
        input_variables=['user_request','task_description','additional_information']
    )

    ARCHITECTURE_PROMPT = PromptTemplate(
        template="""Based on the project overview, describe the high-level architecture for this microservice-based project. Include:
            Project Overview: "{project_overview}"
            1. A diagram or detailed description of the microservice architecture
            2. Key components, data models and their interactions
            3. Data flow between services
            4. External integrations or APIs
            5. Scalability and reliability considerations

            Format your response in markdown, starting with a "## Architecture" heading.""",
        input_variables=['project_overview'],
    )

    FOLDER_STRUCTURE_PROMPT = PromptTemplate(
        template="""
        Given the project overview and architecture:

        Project Overview:
        {project_overview}

        Architecture:
        {architecture}

        Propose a detailed folder structure for this microservice project, adhering to best practices. Include:
        1. Root-level directories
        2. Service-specific directories
        3. Common or shared directories
        4. Test directories
        5. Configuration file locations
        6. Explanation of the purpose for each major directory

        Format your response in markdown, starting with a "## Folder Structure" heading.""",
        input_variables=["project_overview", "architecture"],
    )

    MICROSERVICE_DESIGN_PROMPT = PromptTemplate(
        template="""
            Based on the following project overview and architecture:

            Project Overview:
            {project_overview}
            
            Architecture:
            {architecture}

            For each microservice identified, provide:
            1. Service name and primary responsibility
            2. Key endpoints or functions
            3. Data models or schemas
            4. Internal components or modules
            5. Dependencies on other services or external systems

            Format your response in markdown, starting with a "## Microservice Design" heading, with subheadings for each service.""",
        input_variables=["project_overview","architecture"],
    )

    TASKS_BREAKDOWN_PROMPT = PromptTemplate(
        template="""
            Given the project overview, architecture, and microservice design:

            Project Overview:
            {project_overview}

            Architecture:
            {architecture}

            Microservice Design:
            {microservice_design}

            Break down the project into detailed, self-contained deliverables that team members can work on. Key is to not miss any technical specification for each deliverable, provide:
            1. Deliverable name
            2. Detailed description of what needs to be done
            3. Technical requirements or specifications

            Format your response in markdown, starting with a "## Tasks" heading, with each task as a subheading.""",
        input_variables=["project_overview", "architecture", "microservice_design"],
    )

    STANDARDS_PROMPT = PromptTemplate(
        template="""
            Considering the user request: "{user_request}"
            And the supervisor expectations: "{task_description}"

            Outline the standards to be followed in this project, including:
            1. 12-Factor Application Standards: Explain how each factor applies to this project
            2. Clean Code Standards: Specific practices for maintaining clean, readable code
            3. Code Commenting Standards: Guidelines for effective code documentation
            4. Programming Language Specific Standards: Conventions for the chosen language(s)
            5. User Requested Standards: Any additional standards specified by the user or supervisor

            Format your response in markdown, starting with a "## Standards" heading, with subheadings for each category.""",
        input_variables=["user_request", "task_description"],
    )

    IMPLEMENTATION_DETAILS_PROMPT = PromptTemplate(
        template="""
            Based on the following project details:

            Architecture:
            {architecture}

            Microservice Design:
            {microservice_design}

            Folder Structure:
            {folder_structure}

            Provide specific implementation details for:
            1. list of required source files
            2. list of Configuration files
            3. list of Unit test approach and files
            4. OpenAPI specification (provide a sample structure in YAML)
            5. Dependency management (specify package manager and provide a sample file)
            6. Dockerfile contents
            7. Contents for .dockerignore and .gitignore files

            Format your response in markdown, starting with a "## Implementation Details" heading, with subheadings for each category.""",
        input_variables=["architecture", "microservice_design", "folder_structure"],
    )

    LICENSE_DETAILS_PROMPT = PromptTemplate(
        template="""
            Considering the user request: "{user_request}"
            And the License Text: "{license_text}"

            Specify the license to be used for this project.

            Format your response in markdown, starting with a "## License and Legal Considerations" heading.""",
        input_variables=["user_request", "license_text"],
    )

    def requirements_generation_prompt(self) -> ChatPromptTemplate: 
        """
        This method generates a prompt for the initial project requirements based on the 
        provided Pydantic model.
        
        Returns:
            ChatPromptTemplate: The generated prompt.
        """

        return ChatPromptTemplate.from_template(
            template=self.INITIAL_TEMPLATE,
            partial_variables = {
                "format_instructions": PydanticOutputParser(pydantic_object=RequirementsDoc).get_format_instructions()
            }
        )
    
    def additional_info_prompt(self) -> ChatPromptTemplate:
        """
        This method generates a prompt for providing additional information during 
        project implementation based on the provided Pydantic model.
        
        Returns:
            ChatPromptTemplate: The generated prompt.
        """
                
        return ChatPromptTemplate.from_template(
            template=self.ADDITIONAL_INFO_TEMPLATE,
            partial_variables = {
                "format_instructions": PydanticOutputParser(pydantic_object=QueryResult).get_format_instructions()
            }
        )

    def task_seperation_prompt(self) -> ChatPromptTemplate:
        """
        This method generates a prompt for separating tasks from a markdown document into a list or an array.
        
        Returns:
            ChatPromptTemplate: The generated prompt.
        """

        return ChatPromptTemplate.from_template(
            template=self.TASK_SEPARATION_TEMPLATE,
            partial_variables = {
                "format_instructions": PydanticOutputParser(pydantic_object=TasksList).get_format_instructions()
            }
        )