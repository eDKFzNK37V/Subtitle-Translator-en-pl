import pysubs2

def save_subtitle_lines(lines, file_path):
    ext = file_path.split('.')[-1].lower()
    
    if ext == "ass":
        subs = pysubs2.SSAFile()
        for i, line in enumerate(lines):
            subs.append(pysubs2.SSAEvent(start=i*1000, end=(i+1)*1000, text=line.strip()))
        subs.save(file_path, encoding="utf-8")
    
    elif ext == "srt":
        subs = pysubs2.SSAFile()
        for i, line in enumerate(lines):
            subs.append(pysubs2.SSAEvent(start=i*1000, end=(i+1)*1000, text=line.strip()))
        subs.save(file_path.replace(".srt", ".srt"), encoding="utf-8", format="srt")
    
    elif ext == "txt":
        with open(file_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line.strip() + "\n")
    
    else:
        raise ValueError(f"Unsupported file format: .{ext}")
