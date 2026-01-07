# Script to clean null bytes from views.py file
with open('core/views.py', 'rb') as f:
    content = f.read()
    print(f'Original size: {len(content)} bytes')
    null_count = content.count(b'\x00')
    print(f'Null bytes found: {null_count}')
    
# Remove all null bytes
cleaned = content.replace(b'\x00', b'')

# Write cleaned content back to file
with open('core/views.py', 'wb') as f:
    f.write(cleaned)
    
print(f'Cleaned size: {len(cleaned)} bytes')
print('File cleaned successfully!')