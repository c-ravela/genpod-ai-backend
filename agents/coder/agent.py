"""Coder Agent
"""

from langchain_core.output_parsers import JsonOutputParser

from agents.coder.state import CoderState
from models.constants import ChatRoles, Status
from prompts.coder import coder_prompt

from models.coder import CoderModel

class CoderAgent:
    """
    """

    name = "coder"

    def __init__(self, llm) -> None:
        self.llm = llm

        self.coder_chain = (
            coder_prompt
            | self.llm.with_structured_output(CoderModel)
            | JsonOutputParser()
        )
    
    def node(self, state: CoderState) -> CoderState:
        if state['error']:
            state.toggle_error()

                
        question = f"Here is a task for you to complete {state['current_task']}."
        context = state['project_folder_structure']


        if state['curr_task_status'] == ProgressState.NEW.value:
            coder_solution = self.coder_chain.invoke({"context": context, "coder_tools": coder_tools, "messages": [(ChatRoles.USER.value, question)]})
            expected_keys = [item for item in CoderModel.__annotations__ if item != "description"]

            if state['project_status'] == ProgressState.NEW.value:
                state['project_status'] = ProgressState.PENDING.value

            missing_keys = []
            for key in expected_keys:
                if key not in coder_solution['parsed']:
                    missing_keys.append(key)
            
            if coder_solution['parsing_error']:
                raw_output = coder_solution['raw']
                error = coder_solution['parsing_error']

                state.toggle_error()
                state.add_message(state, (
                    ChatRoles.USER.value,
                    f"ERROR: parsing your output! Be sure to invoke the tool. Output: {raw_output}. \n Parse error: {error}"
                ))
            elif missing_keys:
                state.toggle_error(state)
                state.add_message(state, (
                    ChatRoles.USER.value,
                    f"Now, try again. Invoke the CoderModel tool to structure the output with a steps_to_complete, files_to_create, file_path, code, license_text, project_status and call_next. you missed {missing_keys} in your previous response"
                ))
            else:
                state['coder_response'] = coder_solution['parsed']
                state['file_path'] = coder_solution['parsed']['file_path']
                state['files_to_create'] = coder_solution['parsed']['files_to_create']
                state['code'] = coder_solution['parsed']['code']
                state['license_text'] = coder_solution['parsed']['license_text']
                state['project_status'] = coder_solution['parsed']['project_status']
                state['call_next'] = coder_solution['parsed']['call_next']
                coder_steps = re.split(r'\d+\.\s',state['coder_response']['steps_to_complete'])
                state['coder_steps'] = [coder_step.strip() for coder_step in coder_steps if coder_step!='']
                state['curr_task_status'] = ProgressState.PENDING.value

        if (len(state['pending_tool_calls']) > 0):
            state = set_curr_tool_call_from_pending_tool_calls(state)
            curr_tool_call = get_curr_tool_call(state)
            state.add_message(state, 
                AIMessage(
                    content=f"make a tool_call to '{curr_tool_call['name']}'.",
                    additional_kwargs={
                        'tool_calls': [curr_tool_call],
                    },
                    tool_calls=[curr_tool_call],
                    response_metadata={'finish_reason': 'tool_calls'},
                )
            )
        elif (get_next(state) == GraphNodes.CALL_TOOL.value) and (len(state['coder_steps']) > 0):
            state['current_step'] = next_coder_step(state)

            state = add_message(state, (
                ChatRoles.USER.value,
                state['current_step']
            ))

            temp_state = state.copy()
            del temp_state['messages']

            tool_selector = tool_chain.invoke({'context': f'{temp_state}', 'messages': get_messages_for_prompt(state)})

            print("-----Tool Selector-------")
            pp.pp(tool_selector)
            print("-----Tool Selector-------")
            try:
                ToolChainValidator(content=tool_selector.content, tool_calls=tool_selector.tool_calls, additional_kwargs=tool_selector.additional_kwargs)

                state['pending_tool_calls'] += tool_selector.tool_calls
                state = set_curr_tool_call_from_pending_tool_calls(state)
                curr_tool_call = get_curr_tool_call(state)

                if curr_tool_call != {}:
                    state = add_message(state, 
                        AIMessage(
                            content=f"make a tool_call to '{curr_tool_call['name']}'.",
                            additional_kwargs={
                                'tool_calls': [curr_tool_call],
                            },
                            tool_calls=[curr_tool_call],
                            response_metadata={'finish_reason': 'tool_calls'},
                        )
                    )
                else:
                    print("something is wrong! ", curr_tool_call)

                # (
                #         ChatRoles.AI.value,
                #         f"make a tool_call to '{curr_tool_call['name']}' with args '{curr_tool_call['args']}'."
                #     )
                if state['iterations'] > 0:
                    state['iterations'] = 0
            except Exception:
                    
                if state['iterations'] >= state['max_retry']:
                    state['iterations'] = 0

                    state = add_message(state, (
                        ChatRoles.USER.value,
                        "MaxRetriesError: Max Retries limit reached. Couldn't finish the step: "
                        f" `{state['current_step']}`."
                    ))
                else:
                    state = toggle_error(state)
                    state['iterations'] += 1
                    state['coder_steps'].insert(0, state['current_step'])
                    state['pending_tool_calls'] = []
                    
                    state = add_message(state, (
                        ChatRoles.USER.value,
                        "UnexpectedScenarioOccured: It was unclear whether the tool chain couldn't"
                        " find a suitable tool to complete the task or produced an unintended output"
                        ". An AIMessage with tool calls was expected to be added to the `tool_calls` field in AIMessage" 
                        f"Received: '{tool_selector}'. task:'{state['current_step']}'."
                    ))

            print("DEAD END!!!")
            # if tool_selector.tool_calls:
            #     if len(tool_selector.tool_calls) > 0:
            #         state['pending_tool_calls'] += tool_selector.tool_calls
                
            #     state = set_curr_tool_call_from_pending_tool_calls(state)
            #     curr_tool_call = get_curr_tool_call(state)
            #     if curr_tool_call != {}:
            #         state = add_message(state, (
            #             ChatRoles.AI.value,
            #             f"make a tool_call to '{curr_tool_call['name']}' with args '{curr_tool_call['args']}'."
            #         ))
            # else: # Do I really need to reset the whole coder_steps after this?
            #     # TODO->DONE(error, curr_task_status->New): NEED TO UPDATE few flags accordingly to detect this.
            #     # TODO: This case might lead to a infinte loop.
            #     # Think of the case where similiar task as the previous one is given to the tool_selector
            #     # We will end up in this `else` case. even if the task is re structured we will end up in this case 
            #     # again and again.

            #     # state = toggle_error(state)
            #     # state['curr_task_status'] = TaskState.NEW.value

            #     state = add_message(state, (
            #         ChatRoles.USER.value,
            #         f"ERROR: '{tool_selector}' cannot be used to complete '{state['current_step']}' in the task, give an alternative or better breakdown of the task."
            #     ))
        else: # TODO: What if no tools were assigned? control directly came here?
            state = add_message(state, (
                ChatRoles.AI.value,
                f"The task: `{state['current_task']}` was successfully completed. All the steps:"
                f" `{state['coder_response']['steps_to_complete']}` of the task have been addressed."
                f" The task status: `{TaskState.DONE.value}`, Are there any more tasks?"
            ))
            state['curr_task_status'] = TaskState.AWAITING.value
            state['call_next'] = ""
            state['current_step'] = ""
            state['current_task'] = ""
            state['pending_tool_calls'] = []
            state['coder_steps'] = []

    def router(self, state: CoderState) -> str:

        return "architect"