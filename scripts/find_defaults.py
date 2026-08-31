import os

keywords = ['dbms', 'priya', 'abhi20b02@gmail.com', 'learner@example.com', 'syllabusTopics', 'general']

for root, dirs, files in os.walk('.'):
    if any(x in root for x in ['.venv', '.git', '__pycache__', 'node_modules']):
        continue
    for f in files:
        if f.endswith(('.py', '.js', '.html')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    lines = fp.readlines()
                for i, line in enumerate(lines):
                    for kw in keywords:
                        if kw.lower() in line.lower():
                            print(f"{path}:{i+1} [{kw}] -> {line.strip()[:140]}")
            except Exception as e:
                pass
