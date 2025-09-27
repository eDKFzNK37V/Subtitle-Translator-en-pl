#!/usr/bin/env python3
"""
Test script for CLI callbacks functionality.
Tests the callback system without requiring the full translation pipeline.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from logs import (
    CLIEventData, CLICallbackManager, 
    on_cli_start, on_cli_progress, on_cli_finish, on_cli_error,
    register_cli_callback
)


def test_cli_event_data():
    """Test CLIEventData creation and conversion."""
    print("Testing CLIEventData...")
    
    event = CLIEventData(
        event_type='start',
        input_file='test.srt',
        src_lang='en',
        tgt_lang='pl',
        status='started'
    )
    
    data_dict = event.to_dict()
    assert data_dict['event_type'] == 'start'
    assert data_dict['input_file'] == 'test.srt'
    assert data_dict['src_lang'] == 'en'
    assert data_dict['tgt_lang'] == 'pl'
    assert data_dict['status'] == 'started'
    
    print("✓ CLIEventData works correctly")


def test_callback_manager():
    """Test CLICallbackManager functionality."""
    print("Testing CLICallbackManager...")
    
    manager = CLICallbackManager()
    
    # Test callback registration
    callback_triggered = {'start': False, 'finish': False, 'error': False}
    
    def test_start_callback(event_data):
        callback_triggered['start'] = True
        assert event_data.event_type == 'start'
    
    def test_finish_callback(event_data):
        callback_triggered['finish'] = True
        assert event_data.event_type == 'finish'
    
    def test_error_callback(event_data):
        callback_triggered['error'] = True
        assert event_data.event_type == 'error'
    
    manager.register_callback('on_start', test_start_callback)
    manager.register_callback('on_finish', test_finish_callback)
    manager.register_callback('on_error', test_error_callback)
    
    # Test events
    manager.on_start('test.srt', 'en', 'pl', 'test_pl.srt')
    manager.on_finish('test_pl.srt', 100, 5.2)
    manager.on_error('Test error message', 'test.srt')
    
    assert callback_triggered['start'], "Start callback not triggered"
    assert callback_triggered['finish'], "Finish callback not triggered"
    assert callback_triggered['error'], "Error callback not triggered"
    
    # Test session summary
    summary = manager.get_session_summary()
    assert summary['input_file'] == 'test.srt'
    assert summary['output_file'] == 'test_pl.srt'
    assert summary['src_lang'] == 'en'
    assert summary['tgt_lang'] == 'pl'
    assert summary['errors'] == 1
    assert summary['success'] == False
    
    print("✓ CLICallbackManager works correctly")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing convenience functions...")
    
    # Test with a temporary directory for log output
    with tempfile.TemporaryDirectory() as temp_dir:
        test_file = os.path.join(temp_dir, 'test.srt')
        output_file = os.path.join(temp_dir, 'test_pl.srt')
        
        # Create a fake input file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("1\n00:00:01,000 --> 00:00:03,000\nHello world\n\n")
        
        # Test the callback sequence
        try:
            on_cli_start(test_file, 'en', 'pl', output_file)
            on_cli_progress(25, 100, 'translation')
            on_cli_progress(50, 100, 'translation')
            on_cli_progress(75, 100, 'translation')
            on_cli_progress(100, 100, 'translation')
            on_cli_finish(output_file, 1, 2.5)
            print("✓ Success scenario works correctly")
        except Exception as e:
            print(f"✗ Success scenario failed: {e}")
        
        # Test error scenario
        try:
            on_cli_start('nonexistent.srt', 'en', 'pl')
            on_cli_error('File not found', 'nonexistent.srt')
            print("✓ Error scenario works correctly")
        except Exception as e:
            print(f"✗ Error scenario failed: {e}")


def test_custom_callback_registration():
    """Test custom callback registration through convenience function."""
    print("Testing custom callback registration...")
    
    callback_data = {'events': []}
    
    def custom_callback(event_data):
        callback_data['events'].append(event_data.to_dict())
    
    # Register custom callback
    register_cli_callback('on_start', custom_callback)
    register_cli_callback('on_progress', custom_callback)
    register_cli_callback('on_finish', custom_callback)
    
    # Trigger events
    on_cli_start('test.srt', 'en', 'pl')
    on_cli_progress(50, 100)
    on_cli_finish('test_pl.srt', 100)
    
    # Check that our custom callback received the events
    assert len(callback_data['events']) >= 3, "Custom callback not triggered properly"
    
    event_types = [event['event_type'] for event in callback_data['events']]
    assert 'start' in event_types, "Start event not captured"
    assert 'progress' in event_types, "Progress event not captured"
    assert 'finish' in event_types, "Finish event not captured"
    
    print("✓ Custom callback registration works correctly")


def run_all_tests():
    """Run all CLI callback tests."""
    print("=" * 50)
    print("Testing CLI Callbacks System")
    print("=" * 50)
    
    try:
        test_cli_event_data()
        test_callback_manager()
        test_convenience_functions()
        test_custom_callback_registration()
        
        print("\n" + "=" * 50)
        print("✅ All CLI callback tests passed!")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("=" * 50)
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)