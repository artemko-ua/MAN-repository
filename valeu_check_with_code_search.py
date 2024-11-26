import re
import subprocess
import json
import os
import sys
from io import StringIO
from unittest.mock import patch

LANGUAGES = {
    "python": {"extension": ".py", "command": [sys.executable]},
    "javascript": {"extension": ".js", "command": ["node"]},
    "java": {"extension": ".java", "command": ["javac", "{file}", "&&", "java", "{classname}"]},
    "c": {"extension": ".c", "command": ["gcc", "{file}", "-o", "{basename}", "&&", "./{basename}"]},
    "cpp": {"extension": ".cpp", "command": ["g++", "{file}", "-o", "{basename}", "&&", "./{basename}"]},
}

def parse_text(text):
    """Парсить текст для бібліотек, коду та інструкцій."""
    package_pattern = r'Libraries or dependencies:(.*?)(\n\n|$)'
    code_pattern = r'```(.*?)\n(.*?)```'
    input_pattern = r'@@@(.*?)@@@'
    expected_output_pattern = r'Expected output:(.*?)@@@'

    # Знаходимо всі бібліотеки
    package_match = re.search(package_pattern, text, re.DOTALL)
    libraries = [lib.strip() for lib in package_match.group(1).split(",") if lib.strip()] if package_match else []

    # Знаходимо всі блоки коду
    code_matches = re.finditer(code_pattern, text, re.DOTALL)
    code_snippets = [(match.group(1).strip(), match.group(2).strip()) for match in code_matches]

    # Знаходимо приклади вводу
    input_match = re.search(input_pattern, text, re.DOTALL)
    input_examples = input_match.group(1).strip().split("\n") if input_match else []

    # Знаходимо очікуваний вивід
    expected_output_match = re.search(expected_output_pattern, text, re.DOTALL)
    expected_output = expected_output_match.group(1).strip() if expected_output_match else None

    return libraries, code_snippets, input_examples, expected_output

def install_libraries(language, libraries):
    """Встановлює залежності для вказаної мови програмування."""
    results = []
    for library in libraries:
        try:
            if language == "python":
                command = f"pip install {library}"
            elif language == "javascript":
                command = f"npm install {library}"
            else:
                command = f"echo Unsupported language: {language}"
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            results.append({
                "library": library,
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr
            })
        except Exception as e:
            results.append({"library": library, "success": False, "error": str(e)})
    return results

def save_code_to_file(language, code, file_name="temp"):
    """Зберігає код у файл з відповідним розширенням."""
    ext = LANGUAGES[language]["extension"]
    full_file_name = file_name + ext
    with open(full_file_name, "w") as file:
        file.write(code)
    return full_file_name

def run_code(language, file_name, instructions):
    """Запускає збережений код."""
    cmd = LANGUAGES[language]["command"]
    basename = os.path.splitext(file_name)[0]
    classname = os.path.basename(basename)
    cmd = [part.format(file=file_name, basename=basename, classname=classname) for part in cmd]

    try:
        if language == "python":
            with open(file_name, 'r') as file:
                code = file.read()
            input_iter = iter(instructions)
            with patch('builtins.input', lambda _: next(input_iter)):
                original_stdout = sys.stdout
                sys.stdout = StringIO()
                try:
                    exec(code, {})
                    output = sys.stdout.getvalue()
                finally:
                    sys.stdout = original_stdout
        else:
            result = subprocess.run(cmd, text=True, capture_output=True, input="\n".join(instructions))
            output = result.stdout
        return {"success": True, "output": output.strip()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def generate_report(results):
    """Генерує звіт у JSON-форматі."""
    with open("report.json", "w") as report_file:
        json.dump(results, report_file, indent=4)

if __name__ == "__main__":
    text = """
    Libraries or dependencies: requests, flask

    Code:    
    ```python
    import requests
    print("Hello, World!")
    ```
    @@@ Hello, World! @@@
    """
    
    libraries, code_snippets, input_examples, expected_output = parse_text(text)
    results = []

    for lang_line, code in code_snippets:
        language = lang_line.strip().lower()
        if libraries:
            install_results = install_libraries(language, libraries)
            results.append({"library_install_results": install_results})
        file_name = save_code_to_file(language, code)
        execution_results = run_code(language, file_name, input_examples)
        execution_results["expected_output"] = expected_output
        results.append(execution_results)

    generate_report(results)
    print("Результати виконання збережені у report.json")
