import re
import subprocess
import shlex
from clients.llm_client import invoke_claude
from utils.logger import logger


def extract_kubectl_commands(response_text):
    """
    Extracts all kubectl commands from the model's response text.

    Parameters:
        response_text (str): The response from the model containing the kubectl commands.

    Returns:
        list: A list of extracted kubectl commands. Returns an empty list if no commands are found.
    """
    kubectl_pattern = r"KUBECTL_COMMAND:\s*(kubectl\s[^\n]+)"

    # Find all kubectl commands in the response text
    matches = re.findall(kubectl_pattern, response_text)

    return matches if matches else []


def validate_kubectl_command(command):
    """
    Validates that the kubectl command contains only allowed operations.

    Parameters:
        command (str): The kubectl command to validate.

    Returns:
        bool: True if the command contains an allowed operation, otherwise False.
    """
    ALLOWED_OPERATIONS = {'get', 'describe', 'logs'}

    # Split command and check if operation is allowed
    parts = command.split()
    if len(parts) < 2:
        return False

    operation = parts[1]
    return operation in ALLOWED_OPERATIONS


def execute_kubectl_command(command_str):
    """
    Executes a single kubectl command and returns the output or error.

    Parameters:
        command_str (str): The kubectl command as a string.

    Returns:
        str: The output of the kubectl command if successful, or an error message if the command fails.
    """
    try:
        # Validate command before execution
        if not validate_kubectl_command(command_str):
            return "Error: Command not allowed for security reasons"

        # Escape the command string
        escaped_command = ' '.join(shlex.quote(part)
                                   for part in shlex.split(command_str))
        command_parts = shlex.split(escaped_command)

        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            check=True,
            shell=False
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr}"
    except Exception as e:
        return f"Error processing command: {str(e)}"


def generate_response_with_kubectl(prompt_text, model_option="claude"):
    """
    Generates a response using a model (Claude or TO.DO), executes any kubectl commands found in the response,
    and sends the kubectl results back to the model for further interpretation.

    Parameters:
        prompt_text (str): The input prompt for the model.
        model_option (str): The model option to use ("claude" or "TO.DO"). Default is "claude".

    Returns:
        str: The final response from the model, including interpretation of kubectl output.
    """
    # Step 1: Invoke Claude with the initial prompt
    initial_response = ""
    if model_option == 'claude':
        initial_response = invoke_claude(prompt_text)

    logger.debug(f"Initial Response:\n{initial_response}\n")

    # Step 2: Extract any kubectl commands from the model's response
    kubectl_commands = extract_kubectl_commands(initial_response)
    # Step 3: If kubectl commands are found, execute them
    kubectl_output = []
    if kubectl_commands:
        logger.info(f"Parsed commands:\n{kubectl_commands}\n")
        for command in kubectl_commands:
            output = execute_kubectl_command(command)
            kubectl_output.append(f"Output of '{command}':\n{output}")

        # Combine the initial model response with the kubectl output
        combined_output = prompt_text + "\n\n" + \
            initial_response + "\n\n" + "\n".join(kubectl_output)

        # Step 4: Pass the combined result back to Claude for interpretation
        followup_prompt = f"{combined_output}\n\nPlease interpret the kubectl output above without issuing new kubectl commands."

        # Step 5: Invoke Claude again with the combined response and kubectl results
        final_response = ""
        if model_option == 'claude':
            final_response = invoke_claude(followup_prompt)

        logger.debug(f"Final Response:\n{initial_response}\n")
        return final_response

    # If no kubectl commands were found, return the initial response
    return initial_response
