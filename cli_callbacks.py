# cli_callbacks.py
"""
CLI callback interface for subtitle translation events.
Provides hooks for CLI events (start, progress, finish, error) with comprehensive logging.
"""

import os
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from logs import SubtitleLogger, initialize_session_log, write_session_log


class CLIEventData:
    """Data structure for CLI events containing relevant information."""
    
    def __init__(self, event_type: str, input_file: str = None, output_file: str = None, 
                 src_lang: str = None, tgt_lang: str = None, status: str = None, 
                 error_msg: str = None, progress: tuple = None, log_path: str = None, 
                 timestamp: datetime = None):
        self.event_type = event_type
        self.input_file = input_file
        self.output_file = output_file
        self.src_lang = src_lang
        self.tgt_lang = tgt_lang
        self.status = status
        self.error_msg = error_msg
        self.progress = progress  # (current, total)
        self.log_path = log_path
        self.timestamp = timestamp or datetime.now()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert event data to dictionary for logging."""
        return {
            'event_type': self.event_type,
            'input_file': self.input_file,
            'output_file': self.output_file,
            'src_lang': self.src_lang,
            'tgt_lang': self.tgt_lang,
            'status': self.status,
            'error_msg': self.error_msg,
            'progress': self.progress,
            'log_path': self.log_path,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class CLICallbackManager:
    """
    Manages CLI callbacks and event logging.
    Provides centralized callback registration and event dispatch.
    """
    
    def __init__(self):
        self.callbacks = {
            'on_start': [],
            'on_progress': [],
            'on_finish': [],
            'on_error': []
        }
        self.session_data = {
            'start_time': None,
            'end_time': None,
            'input_file': None,
            'output_file': None,
            'src_lang': None,
            'tgt_lang': None,
            'total_lines': 0,
            'errors': [],
            'events': []
        }
        self.logger: Optional[SubtitleLogger] = None
        
    def register_callback(self, event_type: str, callback: Callable[[CLIEventData], None]):
        """Register a callback for a specific event type."""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
        else:
            raise ValueError(f"Unknown event type: {event_type}")
    
    def _dispatch_event(self, event_data: CLIEventData):
        """Dispatch event to all registered callbacks and log the event."""
        # Store event in session data
        self.session_data['events'].append(event_data.to_dict())
        
        # Update session data based on event type
        if event_data.event_type == 'start':
            self.session_data['start_time'] = event_data.timestamp
            self.session_data['input_file'] = event_data.input_file
            self.session_data['src_lang'] = event_data.src_lang
            self.session_data['tgt_lang'] = event_data.tgt_lang
        elif event_data.event_type == 'finish':
            self.session_data['end_time'] = event_data.timestamp
            self.session_data['output_file'] = event_data.output_file
        elif event_data.event_type == 'error':
            self.session_data['errors'].append(event_data.error_msg)
        
        # Dispatch to registered callbacks
        event_callbacks = self.callbacks.get(f'on_{event_data.event_type}', [])
        for callback in event_callbacks:
            try:
                callback(event_data)
            except Exception as e:
                print(f"Warning: Callback error for {event_data.event_type}: {e}")
    
    def on_start(self, input_file: str, src_lang: str, tgt_lang: str, output_file: str = None):
        """Called when CLI translation starts."""
        # Initialize session logging
        if output_file:
            output_dir = os.path.dirname(output_file)
            initialize_session_log(output_dir)
        else:
            initialize_session_log()
        
        # Create subtitle logger if we have file info
        if input_file and tgt_lang:
            try:
                self.logger = SubtitleLogger(input_file, tgt_lang)
            except Exception as e:
                print(f"Warning: Could not create subtitle logger: {e}")
        
        event_data = CLIEventData(
            event_type='start',
            input_file=input_file,
            output_file=output_file,
            src_lang=src_lang,
            tgt_lang=tgt_lang,
            status='started'
        )
        self._dispatch_event(event_data)
        
        # Console output
        print(f"Starting translation: {os.path.basename(input_file)} ({src_lang} → {tgt_lang})")
        if output_file:
            print(f"Output will be saved to: {os.path.basename(output_file)}")
    
    def on_progress(self, current: int, total: int, stage: str = "processing"):
        """Called during translation progress."""
        event_data = CLIEventData(
            event_type='progress',
            progress=(current, total),
            status=f"{stage}: {current}/{total}"
        )
        self._dispatch_event(event_data)
        
        # Console progress update
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"\r{stage.capitalize()}: {current}/{total} ({percentage:.1f}%)", end='', flush=True)
        
        if current >= total:
            print()  # New line when complete
    
    def on_finish(self, output_file: str, total_lines: int, duration: float = None):
        """Called when CLI translation finishes successfully."""
        # Write session logs
        write_session_log()
        
        # Finalize subtitle logger if available
        if self.logger:
            try:
                self.logger.write_summary()
                log_path = self.logger.get_log_path()
            except Exception as e:
                print(f"Warning: Could not write subtitle log: {e}")
                log_path = None
        else:
            log_path = None
        
        event_data = CLIEventData(
            event_type='finish',
            output_file=output_file,
            status='completed',
            log_path=log_path
        )
        self._dispatch_event(event_data)
        
        # Console output
        print(f"✓ Translation completed successfully!")
        print(f"Output saved to: {output_file}")
        if total_lines > 0:
            print(f"Processed {total_lines} lines")
        if duration:
            print(f"Duration: {duration:.1f}s")
        if log_path and os.path.exists(log_path):
            print(f"Log saved to: {log_path}")
    
    def on_error(self, error_msg: str, input_file: str = None):
        """Called when CLI translation encounters an error."""
        event_data = CLIEventData(
            event_type='error',
            input_file=input_file,
            status='failed',
            error_msg=error_msg
        )
        self._dispatch_event(event_data)
        
        # Console output
        print(f"✗ Translation failed: {error_msg}")
        
        # Still try to write session logs in case of error
        try:
            write_session_log()
        except Exception:
            pass
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of the current CLI session."""
        duration = None
        if self.session_data['start_time'] and self.session_data['end_time']:
            duration = (self.session_data['end_time'] - self.session_data['start_time']).total_seconds()
        
        return {
            'input_file': self.session_data['input_file'],
            'output_file': self.session_data['output_file'],
            'src_lang': self.session_data['src_lang'],
            'tgt_lang': self.session_data['tgt_lang'],
            'duration': duration,
            'total_events': len(self.session_data['events']),
            'errors': len(self.session_data['errors']),
            'success': len(self.session_data['errors']) == 0
        }


# Global callback manager instance
cli_callbacks = CLICallbackManager()


# Convenience functions for direct use
def on_cli_start(input_file: str, src_lang: str, tgt_lang: str, output_file: str = None):
    """Convenience function to trigger CLI start event."""
    cli_callbacks.on_start(input_file, src_lang, tgt_lang, output_file)


def on_cli_progress(current: int, total: int, stage: str = "processing"):
    """Convenience function to trigger CLI progress event."""
    cli_callbacks.on_progress(current, total, stage)


def on_cli_finish(output_file: str, total_lines: int, duration: float = None):
    """Convenience function to trigger CLI finish event."""
    cli_callbacks.on_finish(output_file, total_lines, duration)


def on_cli_error(error_msg: str, input_file: str = None):
    """Convenience function to trigger CLI error event."""
    cli_callbacks.on_error(error_msg, input_file)


def register_cli_callback(event_type: str, callback: Callable[[CLIEventData], None]):
    """Convenience function to register a CLI callback."""
    cli_callbacks.register_callback(event_type, callback)