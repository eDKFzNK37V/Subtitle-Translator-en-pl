import pysubs2

def load_subtitle_lines(file_path):
    ext = file_path.split('.')[-1].lower()
    
    if ext == "ass":
        subs = pysubs2.load(file_path, encoding="utf-8")
        return [event.text for event in subs]
    
    elif ext == "srt":
        subs = pysubs2.load(file_path, encoding="utf-8")
        return [event.text for event in subs]
    
    elif ext == "txt":
        with open(file_path, encoding="utf-8") as f:
            return f.readlines()
    
    else:
        raise ValueError(f"Unsupported file format: .{ext}")
