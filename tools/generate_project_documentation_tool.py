import os
import hashlib
import datetime
import re
import logging
from openai import OpenAI, api_key
from langchain.tools import BaseTool
from utils.logger import logger

# Directories to exclude.
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__"}


def get_file_checksum(file_path):
    """
    Compute the SHA-256 checksum of the file.
    """
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(4096):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        logger.debug("Computed checksum for %s: %s", file_path, checksum)
        return checksum
    except Exception as e:
        logger.error("Error computing checksum for %s: %s", file_path, e)
        return None


def is_text_file(file_path, blocksize=512):
    """
    Check if a file is a text file by attempting to decode its first block as UTF-8.
    Returns True if successful, else False.
    """
    try:
        with open(file_path, 'rb') as f:
            block = f.read(blocksize)
        block.decode('utf-8')
        return True
    except Exception as e:
        logger.warning("File %s is not a text file: %s", file_path, e)
        return False


def get_project_tree(directory):
    """
    Generate a textual tree representation of the project directory,
    excluding directories in EXCLUDE_DIRS.
    """
    logger.info("Generating project tree for directory: %s", directory)
    tree_lines = []
    for root, dirs, files in os.walk(directory):
        # Exclude unwanted directories.
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        # Using os.path.relpath helps get an accurate directory level.
        level = os.path.relpath(root, directory).count(os.sep)
        indent = " " * 4 * level
        tree_lines.append(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 4 * (level + 1)
        for file in files:
            tree_lines.append(f"{subindent}{file}")
    tree = "\n".join(tree_lines)
    logger.debug("Project tree generated:\n%s", tree)
    return tree


def load_existing_documentation(markdown_path):
    """
    Parse an existing markdown file to extract stored sections.
    Expected format for each section:

    ### File: relative/path/to/file.ext
    #### Checksum
    <checksum>
    #### Explanation
    <explanation text that may span multiple lines until the next section or end of file>

    Returns a dict mapping file paths to a dict with keys "checksum" and "explanation".
    """
    if not os.path.exists(markdown_path):
        return {}
    logger.info("Loading existing documentation from %s", markdown_path)
    with open(markdown_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    section_pattern = re.compile(
        r"^### File:\s*(.+?)\s*$\s+^####\s*Checksum\s*$\s+(.+?)\s+^####\s*Explanation\s*$\s+(.*?)(?=^### File:|\Z)",
        re.MULTILINE | re.DOTALL
    )
    docs = {}
    for match in section_pattern.finditer(content):
        file_rel_path = match.group(1).strip()
        checksum = match.group(2).strip()
        explanation = match.group(3).strip()
        docs[file_rel_path] = {"checksum": checksum, "explanation": explanation}
        logger.debug("Parsed documentation for %s with checksum %s", file_rel_path, checksum)
    return docs


def generate_explanation_for_file(file_path, model="gpt-4o-2024-08-06"):
    """
    Reads a file and uses the OpenAI API to generate a markdown explanation.
    The explanation will begin with a level four header, '#### Explanation'.
    For encrypted or binary files, a different explanation is generated.
    """
    logger.info("Generating explanation for file: %s", file_path)
    logger.info("Using model: %s for file explanation", model)
    
    if not is_text_file(file_path):
        return generate_explanation_for_encrypted_file(file_path, model)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        logger.debug("Successfully read file: %s", file_path)
    except Exception as e:
        logger.error("Error reading file %s: %s", file_path, e)
        return f"Error reading file {file_path}: {e}"
    
    prompt = (
        "Provide a detailed explanation for the following code in markdown format. "
        "Your response must begin with exactly the level four header '#### Explanation' on a new line, followed immediately by your detailed explanation. "
        "Do not include any additional headers or text before '#### Explanation'. "
        "Your explanation should cover the code's functionality, purpose, design choices, and any business logic it might implement in a clear and complete manner.\n\n"
        "~~~\n"
        f"{content}\n"
        "~~~"
    )

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        explanation = response.choices[0].message.content.strip()
        logger.info("Explanation generated for file: %s", file_path)
        return explanation
    except Exception as e:
        logger.error("Error generating explanation for file %s: %s", file_path, e)
        return f"Error generating explanation for file {file_path}: {e}"


def generate_explanation_for_encrypted_file(file_path, model="gpt-4o-2024-08-06"):
    """
    Generates a markdown explanation for encrypted or binary files.
    """
    logger.info("Generating explanation for encrypted/binary file: %s", file_path)
    logger.info("Using model: %s for encrypted file explanation", model)
    prompt = (
        "The following file appears to be binary or encrypted and cannot be read as plain text. "
        "Provide a markdown explanation for this file, describing its typical purpose in a code base, "
        "why it might be included, and what its role might be. Also, mention that the file is not readable for analysis.\n\n"
        f"File Name: {os.path.basename(file_path)}"
    )
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        explanation = response.choices[0].message.content.strip()
        logger.info("Explanation generated for encrypted file: %s", file_path)
        return explanation
    except Exception as e:
        logger.error("Error generating explanation for encrypted file %s: %s", file_path, e)
        return f"Error generating explanation for encrypted file {file_path}: {e}"


def format_file_section(rel_path, checksum, explanation):
    """
    Returns a normalized markdown block for a file section.
    """
    norm_checksum = checksum.strip()
    norm_explanation = explanation.strip()
    return (
        f"### File: {rel_path}\n\n"
        f"#### Checksum\n\n{norm_checksum}\n\n"
        f"#### Explanation\n\n{norm_explanation}\n\n"
    )


class GenerateProjectDocumentationTool(BaseTool):
    name: str = "GenerateProjectDocumentationTool"
    description: str = (
        "A tool that generates markdown documentation for a given project directory using incremental updates. "
        "It scans the project directory, computes file checksums, reuses existing explanations when files are unchanged, "
        "and generates or updates documentation accordingly."
    )

    def _run(self, project_directory: str, model: str = "gpt-4o-2024-08-06") -> str:
        # Ensure the OpenAI API key is set.
        if not os.getenv("OPENAI_API_KEY"):
            logger.error("OPENAI_API_KEY environment variable not set.")
            return "Error: OPENAI_API_KEY environment variable not set."

        project_directory = os.path.abspath(project_directory)
        project_name = os.path.basename(project_directory)
        output_file = os.path.join(project_directory, f"{project_name}.md")
        logger.info("Processing project directory: %s", project_directory)
        logger.info("Output file will be: %s", output_file)
        logger.info("Using model: %s for file processing", model)

        # Load previously generated documentation if it exists.
        existing_docs = load_existing_documentation(output_file)

        # Recursively collect all files in the project directory, excluding directories in EXCLUDE_DIRS.
        current_files = {}
        for root, dirs, files in os.walk(project_directory):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                abs_path = os.path.join(root, file)
                # Skip the documentation file itself.
                if os.path.abspath(abs_path) == os.path.abspath(output_file):
                    continue
                rel_path = os.path.relpath(abs_path, project_directory)
                current_files[rel_path] = abs_path

        # Build new documentation info using checksums.
        new_docs = {}
        total_files = len(current_files)
        logger.info("Total files discovered: %d", total_files)

        for idx, (rel_path, abs_path) in enumerate(current_files.items(), start=1):
            logger.info("Processing file %d/%d: %s", idx, total_files, rel_path)
            checksum = get_file_checksum(abs_path)
            if checksum is None:
                continue  # Skip unprocessable files

            # Reuse stored explanation if file's checksum hasn't changed.
            if rel_path in existing_docs and existing_docs[rel_path]["checksum"] == checksum:
                logger.info("No changes detected in %s; reusing previous explanation.", rel_path)
                new_docs[rel_path] = existing_docs[rel_path]
            else:
                logger.info("File %s is new or has changed; generating explanation.", rel_path)
                explanation = generate_explanation_for_file(abs_path, model=model)
                new_docs[rel_path] = {"checksum": checksum, "explanation": explanation}

        # Generate the full markdown content.
        header = (
            f"# Project Documentation: {project_name}\n\n"
            f"_Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n"
        )
        tree_section = "## Project Tree Structure\n\n```\n" + get_project_tree(project_directory) + "\n```\n\n"
        file_sections = "## File Explanations\n\n"
        for rel_path in sorted(new_docs.keys()):
            doc = new_docs[rel_path]
            file_sections += format_file_section(rel_path, doc['checksum'], doc['explanation'])
        
        markdown_content = header + tree_section + file_sections

        # Write the markdown content to the output file.
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            logger.info("Documentation successfully updated in %s", output_file)
        except Exception as e:
            logger.error("Error writing markdown file: %s", e)
            return f"Error writing documentation file: {e}"

        logger.info("Documentation generated successfully in %s", output_file)
        return f"Documentation generated/updated in {output_file}"

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async operation is not supported.")

