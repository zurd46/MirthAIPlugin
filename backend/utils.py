# backend/utils.py

def save_file(path: str, content: str):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def print_panel(title: str, msg: str):
    print("=" * 40)
    print(f"= {title} =")
    print("=" * 40)
    print(msg)
    print("=" * 40)

def print_tree(files: list):
    print("Files generated:")
    for f in files:
        print(f" - {f['path']} ({len(f.get('content_binary', b'')) if f.get('content_binary') is not None else len(f.get('content',''))} bytes)")