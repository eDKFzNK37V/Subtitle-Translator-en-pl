#!/usr/bin/env python3
"""
Example demonstrating CLI callback functionality.
Shows how to register custom callbacks to monitor translation events.
"""

import os
import sys
from cli_callbacks import register_cli_callback, CLIEventData


def detailed_event_logger(event_data: CLIEventData):
    """Example callback that logs detailed event information."""
    print(f"\n[CUSTOM CALLBACK] Event: {event_data.event_type.upper()}")
    print(f"  Timestamp: {event_data.timestamp}")
    
    if event_data.input_file:
        print(f"  Input file: {event_data.input_file}")
    if event_data.output_file:
        print(f"  Output file: {event_data.output_file}")
    if event_data.src_lang or event_data.tgt_lang:
        print(f"  Languages: {event_data.src_lang} → {event_data.tgt_lang}")
    if event_data.status:
        print(f"  Status: {event_data.status}")
    if event_data.progress:
        current, total = event_data.progress
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"  Progress: {current}/{total} ({percentage:.1f}%)")
    if event_data.error_msg:
        print(f"  Error: {event_data.error_msg}")
    if event_data.log_path:
        print(f"  Log path: {event_data.log_path}")


def progress_tracker(event_data: CLIEventData):
    """Example callback that only tracks progress events."""
    if event_data.event_type == 'progress' and event_data.progress:
        current, total = event_data.progress
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"[PROGRESS TRACKER] {percentage:.1f}% complete")


def error_handler(event_data: CLIEventData):
    """Example callback that handles errors."""
    if event_data.event_type == 'error':
        print(f"[ERROR HANDLER] Translation failed!")
        print(f"  File: {event_data.input_file}")
        print(f"  Error: {event_data.error_msg}")
        # Here you could send notifications, write to a separate error log, etc.


def setup_custom_callbacks():
    """Register custom callbacks for CLI events."""
    print("Setting up custom CLI callbacks...")
    
    # Register callbacks for different event types
    register_cli_callback('on_start', detailed_event_logger)
    register_cli_callback('on_progress', detailed_event_logger)
    register_cli_callback('on_finish', detailed_event_logger)
    register_cli_callback('on_error', detailed_event_logger)
    
    # Register specialized callbacks
    register_cli_callback('on_progress', progress_tracker)
    register_cli_callback('on_error', error_handler)
    
    print("Custom callbacks registered successfully!")


def demonstrate_callbacks():
    """Demonstrate callback functionality with simulated events."""
    from cli_callbacks import on_cli_start, on_cli_progress, on_cli_finish, on_cli_error
    
    print("\n" + "="*60)
    print("Demonstrating CLI Callbacks")
    print("="*60)
    
    # Setup callbacks
    setup_custom_callbacks()
    
    print("\nSimulating translation workflow:")
    
    # Simulate a successful translation
    print("\n--- Simulating Success Scenario ---")
    on_cli_start("example.srt", "en", "pl", "example_pl.srt")
    on_cli_progress(25, 100, "translation")
    on_cli_progress(50, 100, "translation")  
    on_cli_progress(75, 100, "translation")
    on_cli_progress(100, 100, "translation")
    on_cli_finish("example_pl.srt", 50, 12.3)
    
    # Simulate an error scenario
    print("\n--- Simulating Error Scenario ---")
    on_cli_start("broken.srt", "en", "pl", "broken_pl.srt")
    on_cli_progress(10, 100, "translation")
    on_cli_error("Model failed to load", "broken.srt")
    
    print("\n" + "="*60)
    print("Callback demonstration completed!")
    print("="*60)


if __name__ == "__main__":
    demonstrate_callbacks()