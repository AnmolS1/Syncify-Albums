"""
Debug Test Harness for Syncify
Run this locally to test the core logic without Docker/Spotify API
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch
import sys

# Mock Spotify data - capture this from your logs once
MOCK_PLAYLIST_DATA = {
	"name": "Test Playlist",
	"tracks": {
		"total": 3,
		"items": [
			{
				"track": {
					"name": "Song One",
					"artists": [{"name": "Artist A"}, {"name": "Artist B"}],
					"album": {"name": "Album Name: Special Edition / 2024"}
				},
				"added_at": "2024-01-01T00:00:00Z"
			},
			{
				"track": {
					"name": "Song Two",
					"artists": [{"name": "Artist C"}],
					"album": {"name": "Different Album"}
				},
				"added_at": "2024-01-02T00:00:00Z"
			},
			{
				"track": {
					"name": "Song One",  # Duplicate
					"artists": [{"name": "Artist A"}],
					"album": {"name": "Album Name: Special Edition / 2024"}
				},
				"added_at": "2024-01-03T00:00:00Z"
			}
		]
	}
}

MOCK_ALBUM_DATA = {
	"name": "Album Name: Special Edition / 2024",
	"items": [
		{
			"name": "Track 1",
			"artists": [{"name": "Artist X"}]
		},
		{
			"name": "Track 2",
			"artists": [{"name": "Artist X"}, {"name": "Artist Y"}]
		}
	]
}


class TestHarness:
	"""Test harness that mimics DataHandler behavior"""
	
	def __init__(self, test_dir=None):
		self.test_dir = test_dir or tempfile.mkdtemp(prefix="syncify_test_")
		self.download_folder = os.path.join(self.test_dir, "downloads")
		os.makedirs(self.download_folder, exist_ok=True)
		print(f"Test directory: {self.test_dir}")
	
	def setup_existing_files(self, files_to_create):
		"""Create mock existing files to test duplicate detection"""
		for album, songs in files_to_create.items():
			album_path = os.path.join(self.download_folder, album)
			os.makedirs(album_path, exist_ok=True)
			for song in songs:
				# Create empty file
				open(os.path.join(album_path, f"{song}.mp3"), 'w').close()
		print(f"Created mock files: {files_to_create}")
	
	def test_spotify_extraction(self, data_handler_class):
		"""Test spotify extractor with mock data"""
		print("\n=== Testing Spotify Extraction ===")
		
		# Mock spotipy
		with patch('spotipy.Spotify') as mock_spotify:
			mock_sp = Mock()
			mock_spotify.return_value = mock_sp
			
			# Test playlist extraction
			mock_sp.playlist.return_value = MOCK_PLAYLIST_DATA
			mock_sp.playlist_items.return_value = {
				"items": MOCK_PLAYLIST_DATA["tracks"]["items"]
			}
			
			handler = data_handler_class()
			handler.download_folder = self.download_folder
			
			result = handler.spotify_extractor("https://open.spotify.com/playlist/test123")
			
			print(f"Extracted {len(result)} tracks")
			for track in result:
				print(f"  - {track['Artist']} - {track['Title']}")
				print(f"	Folder: {track['Folder']}")
			
			return result
	
	def test_duplicate_detection(self, data_handler_class, existing_files):
		"""Test if duplicate detection works correctly"""
		print("\n=== Testing Duplicate Detection ===")
		
		self.setup_existing_files(existing_files)
		
		handler = data_handler_class()
		handler.download_folder = self.download_folder
		
		# Create a test playlist
		test_playlist = {
			"Name": "Test Playlist",
			"Link": "https://open.spotify.com/playlist/test123",
			"Sleep": 0
		}
		
		# Mock the spotify/youtube extraction
		with patch.object(handler, 'spotify_extractor') as mock_extractor:
			# Return tracks that should match existing files
			mock_extractor.return_value = [
				{
					"Artist": "Artist A, Artist B",
					"Title": "Song One",
					"Folder": "Album Name - Special Edition - 2024",
					"Status": "Queued"
				},
				{
					"Artist": "Artist C",
					"Title": "New Song",
					"Folder": "Different Album",
					"Status": "Queued"
				}
			]
			
			with patch.object(handler, 'find_youtube_link', return_value="https://youtube.com/watch?v=test"):
				download_list = handler.get_download_list(test_playlist)
		
		print(f"Songs to download: {len(download_list)}")
		for song in download_list:
			print(f"  - {song['title']}")
		
		# Check what exists
		print("\nExisting files:")
		for root, dirs, files in os.walk(self.download_folder):
			for file in files:
				rel_path = os.path.relpath(os.path.join(root, file), self.download_folder)
				print(f"  - {rel_path}")
		
		return download_list
	
	def cleanup(self):
		"""Clean up test directory"""
		import shutil
		if os.path.exists(self.test_dir):
			shutil.rmtree(self.test_dir)
		print(f"\nCleaned up test directory: {self.test_dir}")


def run_tests():
	"""Run all tests"""
	# Import your actual DataHandler
	# Adjust the import based on your project structure
	try:
		from Syncify import DataHandler
	except ImportError:
		print("Could not import DataHandler. Adjust the import path.")
		return
	
	harness = TestHarness()
	
	try:
		# Test 1: Spotify extraction and folder naming
		tracks = harness.test_spotify_extraction(DataHandler)
		
		# Test 2: Duplicate detection with existing files
		existing_files = {
			"Album Name - Special Edition - 2024": [
				"Song One - Artist A, Artist B"
			],
			"Different Album": []
		}
		
		download_list = harness.test_duplicate_detection(DataHandler, existing_files)
		
		# Assertions
		print("\n=== Test Results ===")
		assert len(download_list) == 1, f"Expected 1 song to download, got {len(download_list)}"
		print("✓ Duplicate detection working correctly")
		
	finally:
		harness.cleanup()


if __name__ == "__main__":
	run_tests()