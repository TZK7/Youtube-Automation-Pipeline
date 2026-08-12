import os


def sanitize_filename(text, max_length=25):
    return "".join(c if c.isalnum() else "_" for c in str(text)).strip("_")[:max_length]


def get_project_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
