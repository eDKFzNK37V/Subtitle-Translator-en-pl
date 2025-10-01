"""
Simplified progress controller for GUI translation progress tracking.
"""

import time


class ProgressController:
    """Simple progress controller for translation GUI."""
    
    def __init__(self, root, progress_var, translation_label, post_label, status_label):
        self.root = root
        self.progress_var = progress_var
        self.translation_label = translation_label
        self.post_label = post_label
        self.status_label = status_label
        
        # Progress tracking
        self.start_time = 0.0
        self.t_total = 0
        self.p_total = 0
        self.t_current = 0
        self.p_current = 0
    
    def start(self, translation_lines):
        """Start progress tracking."""
        self.t_total = translation_lines
        self.p_total = translation_lines
        self.t_current = 0
        self.p_current = 0
        self.start_time = time.time()
        
        # Reset UI
        self.progress_var.set(0)
        self.translation_label.config(text="Translation: 0%")
        self.post_label.config(text="Post-processing: waiting")
        self.status_label.config(text="Starting...")
    
    def update_translation(self, current, total):
        """Update translation progress."""
        self.t_current = current
        self.t_total = max(self.t_total, total)
        
        if total > 0:
            pct = (current / total) * 100
            self.translation_label.config(text=f"Translation: {int(pct)}%")
            
            # Overall progress (translation is 50% of total)
            overall_pct = (current / total) * 50
            self.progress_var.set(overall_pct)
            self.status_label.config(text=f"{int(overall_pct)}%")
        
        self.root.update_idletasks()
    
    def update_post_processing(self, current, total):
        """Update post-processing progress."""
        self.p_current = current
        self.p_total = max(self.p_total, total)
        
        if total > 0:
            pct = (current / total) * 100
            self.post_label.config(text=f"Post-processing: {int(pct)}%")
            
            # Overall progress (post-processing is second 50% of total)
            overall_pct = 50 + (current / total) * 50
            self.progress_var.set(overall_pct)
            self.status_label.config(text=f"{int(overall_pct)}%")
        
        self.root.update_idletasks()
    
    def finish(self):
        """Mark progress as complete."""
        self.progress_var.set(100)
        self.translation_label.config(text="Translation: 100%")
        self.post_label.config(text="Post-processing: 100%")
        
        elapsed = time.time() - self.start_time
        self.status_label.config(text=f"Complete! ({elapsed:.1f}s)")
        
        self.root.update_idletasks()
