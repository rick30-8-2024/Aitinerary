"""
Test script for YouTube Video Service using Google GenAI.
Tests travel information extraction from YouTube videos.
"""

import asyncio
import json


async def test_single_video_extraction():
    """Test extracting travel information from a single video."""
    print("\n" + "=" * 60)
    print("Test 1: Single Video - Travel Information Extraction")
    print("=" * 60)
    
    from services.youtube_video_service import youtube_video_service
    
    youtube_url = "https://www.youtube.com/watch?v=6igdCnYjBt4"
    
    print(f"\nYouTube URL: {youtube_url}")
    print("\nExtracting travel information...")
    
    try:
        travel_info = await youtube_video_service.extract_travel_info(youtube_url)
        
        print(f"\n{'=' * 40}")
        print("EXTRACTED TRAVEL INFORMATION")
        print(f"{'=' * 40}")
        
        print(f"\n📍 Destination: {travel_info.destination}")
        print(f"\n📝 Summary: {travel_info.summary}")
        
        if travel_info.places:
            print(f"\n🏛️ Places to Visit ({len(travel_info.places)}):")
            for place in travel_info.places[:10]:
                print(f"   - {place.name} ({place.category})")
                if place.description:
                    print(f"     {place.description[:100]}...")
        
        if travel_info.activities:
            print(f"\n🎯 Activities ({len(travel_info.activities)}):")
            for activity in travel_info.activities[:10]:
                print(f"   - {activity.name}")
                if activity.tips:
                    print(f"     Tip: {activity.tips[:100]}...")
        
        if travel_info.hidden_gems:
            print(f"\n💎 Hidden Gems ({len(travel_info.hidden_gems)}):")
            for gem in travel_info.hidden_gems[:5]:
                print(f"   - {gem.name}: {gem.why_special[:100]}...")
        
        if travel_info.food_recommendations:
            print(f"\n🍽️ Food Recommendations ({len(travel_info.food_recommendations)}):")
            for food in travel_info.food_recommendations[:5]:
                print(f"   - {food.name}")
                if food.location:
                    print(f"     Location: {food.location}")
        
        if travel_info.travel_tips:
            print(f"\n💡 Travel Tips ({len(travel_info.travel_tips)}):")
            for tip in travel_info.travel_tips[:5]:
                print(f"   - [{tip.category}] {tip.tip[:100]}...")
        
        if travel_info.best_time_to_visit:
            print(f"\n📅 Best Time to Visit: {travel_info.best_time_to_visit}")
        
        if travel_info.budget_info:
            print(f"\n💰 Budget Info: {travel_info.budget_info}")
        
        if travel_info.duration_suggested:
            print(f"\n⏱️ Suggested Duration: {travel_info.duration_suggested}")
        
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_video_transcript():
    """Test getting transcript from a video."""
    print("\n" + "=" * 60)
    print("Test 2: Video Transcript Extraction")
    print("=" * 60)
    
    from services.youtube_video_service import youtube_video_service
    
    youtube_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    print(f"\nYouTube URL: {youtube_url}")
    print("(First YouTube video - 'Me at the zoo')")
    print("\nExtracting transcript...")
    
    try:
        transcript = await youtube_video_service.get_transcript(youtube_url)
        print(f"\nTranscript:\n{transcript}")
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_video_summary():
    """Test getting summary from a video."""
    print("\n" + "=" * 60)
    print("Test 3: Video Summary")
    print("=" * 60)
    
    from services.youtube_video_service import youtube_video_service
    
    youtube_url = "https://www.youtube.com/watch?v=6igdCnYjBt4"
    
    print(f"\nYouTube URL: {youtube_url}")
    print("\nGetting video summary...")
    
    try:
        summary = await youtube_video_service.summarize_video(youtube_url)
        print(f"\nSummary:\n{summary}")
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        return False


async def test_multiple_videos():
    """Test extracting travel info from multiple videos."""
    print("\n" + "=" * 60)
    print("Test 4: Multiple Videos Processing")
    print("=" * 60)
    
    from services.youtube_video_service import youtube_video_service
    
    youtube_urls = [
        "https://www.youtube.com/watch?v=6igdCnYjBt4",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    ]
    
    print(f"\nProcessing {len(youtube_urls)} videos...")
    for url in youtube_urls:
        print(f"  - {url}")
    
    try:
        multi_info = await youtube_video_service.extract_travel_info_from_multiple(youtube_urls)
        
        print(f"\n{'=' * 40}")
        print("COMBINED TRAVEL INFORMATION")
        print(f"{'=' * 40}")
        
        print(f"\n📍 Combined Destinations: {multi_info.combined_destination}")
        print(f"\n📊 Summary:")
        print(f"   - Videos processed: {len(multi_info.videos)}")
        print(f"   - Total unique places: {len(multi_info.all_places)}")
        print(f"   - Total unique activities: {len(multi_info.all_activities)}")
        print(f"   - Total hidden gems: {len(multi_info.all_hidden_gems)}")
        print(f"   - Total food recommendations: {len(multi_info.all_food_recommendations)}")
        print(f"   - Total travel tips: {len(multi_info.all_travel_tips)}")
        
        if multi_info.all_places:
            print(f"\n🏛️ All Unique Places:")
            for place in multi_info.all_places[:10]:
                print(f"   - {place.name} ({place.category})")
        
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_json_output():
    """Test getting travel info as JSON for itinerary generation."""
    print("\n" + "=" * 60)
    print("Test 5: JSON Output for Itinerary Generation")
    print("=" * 60)
    
    from services.youtube_video_service import youtube_video_service
    
    youtube_url = "https://www.youtube.com/watch?v=6igdCnYjBt4"
    
    print(f"\nYouTube URL: {youtube_url}")
    print("\nExtracting as JSON...")
    
    try:
        travel_info = await youtube_video_service.extract_travel_info(youtube_url)
        
        json_output = travel_info.model_dump_json(indent=2)
        print(f"\nJSON Output (first 2000 chars):\n{json_output[:2000]}...")
        
        return True
        
    except Exception as e:
        print(f"\nError: {e}")
        return False


async def main():
    """Main function to run all tests."""
    print("=" * 60)
    print("YouTube Video Service Test")
    print("Using Gemini's Native Video Processing")
    print("=" * 60)
    
    try:
        from services.youtube_video_service import youtube_video_service
        print("✓ YouTube Video Service imported successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return
    except Exception as e:
        print(f"✗ Initialization error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    tests = [
        ("Single Video Extraction", test_single_video_extraction),
        ("Video Transcript", test_video_transcript),
        ("Video Summary", test_video_summary),
        ("Multiple Videos", test_multiple_videos),
        ("JSON Output", test_json_output),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
                print(f"\n✓ {test_name} - PASSED")
            else:
                failed += 1
                print(f"\n✗ {test_name} - FAILED")
        except Exception as e:
            failed += 1
            print(f"\n✗ {test_name} - FAILED: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if passed > 0:
        print("""
SUCCESS! The YouTube Video Service can:
1. Extract travel information directly from videos
2. Get video transcripts
3. Summarize videos
4. Process multiple videos and combine info
5. Output structured JSON for itinerary generation

This can replace the youtube-transcript-api approach!
""")


if __name__ == "__main__":
    asyncio.run(main())
