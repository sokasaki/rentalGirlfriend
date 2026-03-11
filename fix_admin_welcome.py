"""Fix Welcome message in all admin templates to use current_user.display_name."""
import re, os, glob

templates_dir = r'd:\python\Rental-V1\rentalGirlfriend\templates\admin'

# Patterns to replace
patterns = [
    # Pattern 1: the common inline conditional
    (
        r"\{\{\s*'Admin' if is_admin else current_user\.username if\s*current_user else 'Admin'\s*\}\}",
        "{{ current_user.display_name if current_user else 'Admin' }}"
    ),
    # Pattern 2: view_detail variant
    (
        r"\{\{\s*current_user\.username if current_user else 'Admin'\s*\}\}",
        "{{ current_user.display_name if current_user else 'Admin' }}"
    ),
]

files = glob.glob(os.path.join(templates_dir, '**', '*.html'), recursive=True)
changed = 0

for filepath in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content
    for pattern, replacement in patterns:
        new_content = re.sub(pattern, replacement, new_content)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✓ {os.path.relpath(filepath, templates_dir)}")
        changed += 1

print(f"\nDone! Updated {changed} file(s).")
