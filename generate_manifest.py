import os
import json
import argparse
from datetime import datetime, timezone

# Configurações
OMIT_FILES = {
    'generate_manifest.py', 'README.md', '.github', '.git', 'index.html',
    'CNAME', 'manifest.json', 'site-src', 'node_modules', 'dist',
    'convert_to_webp.py', '.gitattributes', '.gitignore', 'requirements.txt'
}
OMIT_DIRS = {
    '.git', '.github', 'site-src', 'node_modules', 'dist',
    '__pycache__', 'scripts', 'admin'
}

# Image extensions that should be grouped as variants
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg'}


def get_file_info(path, relative_path):
    """Retorna metadados do arquivo."""
    try:
        stat = os.stat(path)
        name = os.path.basename(path)
        _, ext = os.path.splitext(name)
        return {
            'name': name,
            'path': relative_path.replace('\\', '/'),
            'type': 'file',
            'size': stat.st_size,
            'ext': ext.lower()
        }
    except Exception as e:
        print(f"Erro ao ler arquivo {path}: {e}")
        return None


def group_image_variants(files):
    """
    Groups image files by base name, producing a single entry per image
    with a 'variants' list of all available formats.
    Non-image files are passed through unchanged.
    """
    image_groups = {}
    non_images = []

    for f in files:
        ext = f.get('ext', '')
        if ext in IMAGE_EXTENSIONS:
            base_name = f['name'][:f['name'].rfind('.')] if '.' in f['name'] else f['name']
            if base_name not in image_groups:
                image_groups[base_name] = []
            image_groups[base_name].append(f)
        else:
            non_images.append(f)

    grouped = []
    for base_name, variants in image_groups.items():
        # Sort variants: prefer webp > png > jpg > jpeg > others
        priority = {'.webp': 0, '.png': 1, '.jpg': 2, '.jpeg': 3, '.gif': 4, '.svg': 5}
        variants.sort(key=lambda v: priority.get(v['ext'], 99))

        primary = variants[0]
        entry = {
            'name': primary['name'],
            'path': primary['path'],
            'type': 'file',
            'size': primary['size'],
            'baseName': base_name,
            'variants': [
                {
                    'ext': v['ext'],
                    'path': v['path'],
                    'size': v['size']
                } for v in variants
            ]
        }
        grouped.append(entry)

    # Combine and sort alphabetically
    result = non_images + grouped
    result.sort(key=lambda x: x.get('baseName', x['name']).lower())

    return result


def scan_directory(directory, root_dir):
    """Escaneia recursivamente o diretório."""
    items = []

    try:
        with os.scandir(directory) as it:
            for entry in it:
                if entry.name in OMIT_FILES or entry.name in OMIT_DIRS:
                    continue

                relative_path = os.path.relpath(entry.path, root_dir)

                if entry.is_dir():
                    children = scan_directory(entry.path, root_dir)
                    items.append({
                        'name': entry.name,
                        'path': relative_path.replace('\\', '/'),
                        'type': 'directory',
                        'children': children
                    })
                elif entry.is_file():
                    file_info = get_file_info(entry.path, relative_path)
                    if file_info:
                        items.append(file_info)
    except Exception as e:
        print(f"Erro ao acessar diretório {directory}: {e}")

    # Separate directories and files
    directories = sorted(
        [i for i in items if i['type'] == 'directory'],
        key=lambda x: x['name'].lower()
    )
    files = [i for i in items if i['type'] == 'file']

    # Group image variants
    grouped_files = group_image_variants(files)

    return directories + grouped_files


def count_stats(tree):
    """Count total unique items and total size."""
    total_files = 0
    total_size = 0

    for item in tree:
        if item['type'] == 'directory':
            sub_files, sub_size = count_stats(item.get('children', []))
            total_files += sub_files
            total_size += sub_size
        else:
            total_files += 1
            # Count primary variant size only
            total_size += item.get('size', 0)

    return total_files, total_size


def main():
    parser = argparse.ArgumentParser(description="Gera manifest.json para o mri assets.")
    parser.add_argument('--root', default='.', help='Diretório raiz para escanear')
    parser.add_argument('--output', default='manifest.json', help='Arquivo de saída')

    args = parser.parse_args()

    print(f"Escaneando diretório: {os.path.abspath(args.root)}")

    tree = scan_directory(args.root, args.root)

    total_files, total_size = count_stats(tree)

    manifest = {
        'root': tree,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'stats': {
            'total_files': total_files,
            'total_size': total_size
        }
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest gerado em: {os.path.abspath(args.output)}")
    print(f"  Arquivos únicos: {total_files}")
    if total_size > 1_048_576:
        print(f"  Tamanho total: {total_size / 1_048_576:.1f} MB")
    else:
        print(f"  Tamanho total: {total_size / 1024:.1f} KB")


if __name__ == '__main__':
    main()
