#!/usr/bin/env python3
"""
Subtitle Post-Processing Script
Auto-detects subtitle format (.ass, .srt, .txt) and applies custom punctuation/flexion corrections.
Uses polish_punctation.json for Polish punctuation rules.
"""
import sys
import os
import re
import json
json_path = 'polish_punctuation.json'
# Example: Polish flexion/punctuation correction (placeholder)
def load_punctuation_rules(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['polish_punctuation_rules']

# Basic punctuation correction using rules from JSON
def correct_text(text, rules):
    # Spacing before/after punctuation
    spacing_rules = rules.get('spacing', {}).get('rules', [])
    for rule in spacing_rules:
        if rule['id'] == 'spacing_basic':
            # No space before comma, period, semicolon, colon; one space after
            text = re.sub(r'\s+([,.;:])', r'\1', text)
            text = re.sub(r'([,.;:])(\S)', r'\1 \2', text)
        if rule['id'] == 'spacing_dash':
            # Spaces around em dash
            text = re.sub(r'\s*—\s*', ' — ', text)
        # Add more spacing rules as needed

    # Comma rules (example: enumeration)
    comma_rules = rules.get('comma', {}).get('rules', [])
    for rule in comma_rules:
        if rule['id'] == 'comma_enumeration':
            # Add comma between list items (very basic, for demonstration)
            text = re.sub(r'([a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+) ([a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+) ([a-ząćęłńóśźżA-ZĄĆĘŁŃÓŚŹŻ]+)', r'\1, \2, \3', text)
        # Add more comma rules as needed

    # Period at end of sentence
    period_rules = rules.get('period', {}).get('rules', [])
    for rule in period_rules:
        if rule['id'] == 'period_end_sentence':
            if not text.strip().endswith('.'):
                text += '.'
    # Add more period rules as needed

    # TODO: Implement more rules from JSON as needed
    return text

def process_ass(input_path, output_path, rules):
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        if line.startswith('Dialogue:'):
            parts = line.split(',', 9)
            if len(parts) >= 10:
                # Only correct the subtitle text (10th field)
                parts[9] = correct_text(parts[9].rstrip('\n'), rules) + '\n'
                line = ','.join(parts)
        new_lines.append(line)
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.writelines(new_lines)

def process_srt(input_path, output_path, rules):
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()
    blocks = re.split(r'\n\s*\n', content.strip())
    new_blocks = []
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            # index, timestamp, text...
            index = lines[0]
            timestamp = lines[1]
            text_lines = [correct_text(line, rules) for line in lines[2:]]
            new_block = '\n'.join([index, timestamp] + text_lines)
        else:
            new_block = block
        new_blocks.append(new_block)
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.write('\n\n'.join(new_blocks) + '\n')

def process_txt(input_path, output_path, rules):
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()
    new_lines = [correct_text(line.rstrip('\n'), rules) + '\n' for line in lines]
    with open(output_path, 'w', encoding='utf-8-sig') as f:
        f.writelines(new_lines)

def main():
    if len(sys.argv) < 2:
        print('Usage: python postprocess_subtitles.py <input_file> [output_file]')
        sys.exit(1)
    input_path = sys.argv[1]
    if not os.path.exists(input_path):
        print(f'File not found: {input_path}')
        sys.exit(1)
    ext = input_path.rsplit('.', 1)[-1].lower()
    output_path = sys.argv[2] if len(sys.argv) > 2 else input_path.rsplit('.', 1)[0] + '_post.' + ext
    # Load punctuation rules from JSON
    rules_path = os.path.join(os.path.dirname(__file__), 'polish_punctation.json')
    if not os.path.exists(rules_path):
        print(f'Rules file not found: {rules_path}')
        sys.exit(1)
    rules = load_punctuation_rules(rules_path)

    if ext == 'ass':
        process_ass(input_path, output_path, rules)
    elif ext == 'srt':
        process_srt(input_path, output_path, rules)
    elif ext == 'txt':
        process_txt(input_path, output_path, rules)
    else:
        print(f'Unsupported file type: {ext}')
        sys.exit(1)
    print(f'Post-processed file saved to: {output_path}')

if __name__ == '__main__':
    main()
