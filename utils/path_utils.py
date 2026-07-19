import os
import sys


def _search_roots():
    if getattr(sys, 'frozen', False):
        # onedir держит файлы рядом с exe, onefile распаковывает их в _MEIPASS.
        roots = [os.path.dirname(os.path.abspath(sys.executable))]
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            roots.append(meipass)
        return roots
    # Каталог проекта, а не текущая рабочая папка: раньше ресурсы терялись,
    # если программу запускали не из её собственной директории.
    return [os.path.dirname(os.path.dirname(os.path.abspath(__file__)))]


def resource_path(relative_path):
    roots = _search_roots()
    for root in roots:
        candidate = os.path.join(root, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(roots[0], relative_path)
