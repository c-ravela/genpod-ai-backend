from typing import List

from agents.supervisor.supervisor_state import SupervisorState
from apis.microservice.controller import MicroserviceController
from apis.microservice.entity import Microservice
from apis.project.controller import ProjectController
from apis.project.entity import Project
from apis.session.controller import SessionController
from apis.session.entity import Session
from configs.project_config import ProjectAgents, ProjectGraphs
from genpod.team import TeamMembers


def generate(
        project: Project,
        agents: ProjectAgents,
        graphs: ProjectGraphs,
        database_path: str,
        collection_name: str,
        vector_db_path: str,
        graph_recursion_limit: int
    ):
    """Generate the microservice"""

    while True:
        try:
            print("\nEnter the prompt to define your project idea (at least 10 characters): ")
            user_prompt = input("> ").strip()
            
            if len(user_prompt) > 9:
                print(f"\nPrompt accepted: {user_prompt}")
                break
            else:
                print("Invalid input. Please provide a detailed description of your project idea (at least 10 characters).")
        except Exception as e:
            print(f"An error occurred while processing your input: {e}")

    microservice_controller = MicroserviceController()
    session_controller = SessionController()

    microservice = Microservice(
        microservice_name="",
        project_id=project.id,
        status="",
        created_by=project.created_by
    )

    microservice = microservice_controller.create(microservice)
    for agent in agents:
        curr_session = Session(
            agent_id=agent.agent_id,
            project_id=project.id,
            microservice_id=microservice.id,
            created_by=project.created_by
        )
        curr_session = session_controller.create(curr_session)
        agent.set_thread_id(curr_session.id)

    genpod_team = TeamMembers(agents, graphs, database_path, collection_name, vector_db_path)
    genpod_team.supervisor.set_recursion_limit(graph_recursion_limit)
    genpod_team.supervisor.graph.agent.setup_team(genpod_team)

    supervisor_response = genpod_team.supervisor.stream(
        {   
            "project_id":project.id,
            "microservice_id": microservice.id,
            "original_user_input": user_prompt,
            "project_path": project.project_location,
            "license_url": project.license_text,
            "license_text": project.license_file_url,
        }
    )

    result: SupervisorState = None
    should_update = False
    for res in supervisor_response:
        for node_name, super_state in res.items():
            result = super_state

            if microservice.microservice_name != super_state['microservice_name']:
                microservice.microservice_name = super_state['microservice_name']
                should_update = True
            
            if microservice.status != super_state['project_status']:
                microservice.status = str(super_state['project_status'])
                should_update = True

            if should_update:
                microservice_controller.update(microservice, microservice.created_by)
                should_update = False

    print(
        f"Project generated successfully! Project ID: {result['project_id']}, "
        f"Project Name: {result['project_name']}, Location: {project.project_location}."
    )

def resume(
    user_id: int,
    agents: ProjectAgents,
    graphs: ProjectGraphs,
    database_path: str,
    collection_name: str,
    vector_db_path: str,
    graph_recursion_limit: int
):  
    microservice_controller = MicroserviceController()
    picked_project_id = get_project_details(user_id)
    picked_microservice = get_microservice_details(user_id, picked_project_id)
    session_details = get_session_details(user_id, picked_project_id, picked_microservice.id)

    session_map = {session.agent_id: session for session in session_details}
    
    for agent in agents:
        curr_session = session_map.get(agent.agent_id)
        if curr_session:
            agent.set_thread_id(curr_session.id)
    
    genpod_team = TeamMembers(agents, graphs, database_path, collection_name, vector_db_path)
    genpod_team.supervisor.set_recursion_limit(graph_recursion_limit)
    genpod_team.supervisor.graph.agent.setup_team(genpod_team)

    supervisor_response = genpod_team.supervisor.stream(genpod_team.supervisor.get_last_saved_state())

    result: SupervisorState = None
    should_update = False
    for res in supervisor_response:
        for node_name, super_state in res.items():
            result = super_state

            if picked_microservice.microservice_name != super_state['microservice_name']:
                picked_microservice.microservice_name = super_state['microservice_name']
                should_update = True
            
            if picked_microservice.status != super_state['project_status']:
                picked_microservice.status = str(super_state['project_status'])
                should_update = True

            if should_update:
                microservice_controller.update(picked_microservice, picked_microservice.created_by)
                should_update = False

    print(
        f"Project generated successfully! Project ID: {result['project_id']}, "
        f"Project Name: {result['project_name']}, Location: {result['project_path']}."
    )

def get_project_details(user_id: int) -> int:
    project_controller = ProjectController()

    user_projects = project_controller.get_projects(user_id)
    if not user_projects:
        print(f"\nNo projects found for the user with ID {user_id}.")
        return
    
    print(f"\nListing projects created by the user with ID {user_id}:\n")
    for project in user_projects:
        print(
            f"Project Details:\n"
            f"  - ID: {project.id}\n"
            f"  - Name: {project.project_name}\n"
        )

    # Prompt the user to select a project
    while True:
        try:
            print("Please enter the ID of the project you want to select")
            picked_project_id = int(input("> "))
            if __validate_project_id(picked_project_id, user_projects):
                print(f"\nProject with ID {picked_project_id} selected successfully!")
                return picked_project_id
            else:
                print("Invalid project ID. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a numeric project ID.")

def __validate_project_id(id: int, projects: List[Project]):
    return any(project.id == id for project in projects)

def get_microservice_details(user_id: int, project_id: int) -> Microservice:
    microservice_controller = MicroserviceController()

    microservices = microservice_controller.get_microservices(project_id, user_id)
    if not microservices:
        print(f"\nNo microservices found for the project with ID {project_id}.")
        return
    
    print(f"\nListing incomplete microservices for the project with ID {project_id} and user ID {user_id}:\n")
    
    # Display microservices that are not marked as "DONE"
    active_microservices = {
        ms.id: ms for ms in microservices if ms.status != "DONE"
    }
    if not active_microservices:
        print("All microservices for this project are marked as 'DONE' and cannot be resumed.")
        return None
        
    for id, microservice in active_microservices.items():
            print(
                f"Microservice Details:\n"
                f"  - ID: {id}\n"
                f"  - Name: {microservice.microservice_name}\n"
                f"  - Project ID: {microservice.project_id}\n"
                f"  - Status: {microservice.status}\n"
            )

    # Prompt user to select a microservice
    while True:
        try:
            print("\nPlease enter the ID of the microservice you want to resume:")
            pick = int(input("> "))
            if pick in active_microservices:
                selected_microservice = active_microservices[pick]
                print(
                    f"\nMicroservice '{selected_microservice.microservice_name}' "
                    f"(ID: {pick}) has been selected for resumption successfully!"
                )

                return selected_microservice
            else:
                print("Invalid microservice ID. Please enter a valid ID from the list above.")
        except ValueError:
            print("Invalid input. Please enter a numeric microservice ID.")

def get_session_details(user_id: int, project_id: int, microservice_id: int) -> List[Session]:
    session_controller = SessionController()
    sessions = session_controller.get_sessions(project_id, microservice_id, user_id)
    if not sessions:
        print(f"\nNo sessions found for the microservice with ID {microservice_id}.")
        return
    
    return sessions
