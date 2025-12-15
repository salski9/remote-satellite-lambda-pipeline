#!/usr/bin/env python3
"""
Continuous Multimodal Stream Producer
Produces events continuously until interrupted
"""
import os
import sys
import time
import signal
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.producer.kafka_producer_multimodal import produce_multimodal_events

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    print('\n\n🛑 Shutting down gracefully...')
    running = False

def main():
    parser = argparse.ArgumentParser(description='Continuous Multimodal Stream Producer')
    parser.add_argument('--batch-size', type=int, default=100, 
                        help='Events per batch (default: 100)')
    parser.add_argument('--delay', type=float, default=0.001, 
                        help='Delay between events in seconds (default: 0.001)')
    parser.add_argument('--batch-interval', type=int, default=10,
                        help='Seconds between batches (default: 10)')
    parser.add_argument('--max-events', type=int, default=None,
                        help='Maximum total events (default: unlimited)')
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("="*80)
    print("CONTINUOUS MULTIMODAL STREAM PRODUCER")
    print("="*80)
    print(f"Batch size: {args.batch_size}")
    print(f"Delay per event: {args.delay}s")
    print(f"Batch interval: {args.batch_interval}s")
    print(f"Max events: {args.max_events or 'unlimited'}")
    print("\nPress Ctrl+C to stop gracefully...")
    print("="*80)
    print()
    
    batch_num = 0
    total_produced = 0
    
    while running:
        batch_num += 1
        
        # Determine batch size
        batch_size = args.batch_size
        if args.max_events:
            remaining = args.max_events - total_produced
            if remaining <= 0:
                break
            batch_size = min(batch_size, remaining)
        
        print(f"\n📦 Batch #{batch_num} - Producing {batch_size} events...")
        
        try:
            # Produce batch
            from src.producer.kafka_producer_multimodal import produce_multimodal_events
            success, fail = produce_multimodal_events(
                limit=batch_size, 
                delay=args.delay,
                topic='multimodal-events'
            )
            
            total_produced += success
            
            print(f"✓ Batch complete: {success} events | Total: {total_produced}")
            
            # Check if we've reached max events
            if args.max_events and total_produced >= args.max_events:
                print(f"\n✓ Reached maximum events: {args.max_events}")
                break
            
            # Wait before next batch
            if running:
                print(f"⏳ Waiting {args.batch_interval}s before next batch...")
                for i in range(args.batch_interval):
                    if not running:
                        break
                    time.sleep(1)
        
        except Exception as e:
            print(f"❌ Error in batch {batch_num}: {e}")
            time.sleep(5)
    
    print("\n" + "="*80)
    print(f"STREAM PRODUCER STOPPED")
    print(f"Total events produced: {total_produced}")
    print("="*80)

if __name__ == '__main__':
    main()
