#!/usr/bin/env python3
"""
UserProfile Module - User Profile Management System

This module provides a comprehensive UserProfile class for managing user data,
including profile creation, persistence to JSON, favorite phrase management,
and usage statistics tracking.

Author: EyeTrackerWeb Project
Date: 2025
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional


class UserProfile:
    """
    A class to manage user profiles with persistence capabilities.
    
    Attributes:
        user_id (str): Unique identifier for the user
        username (str): User's name
        email (str): User's email address
        favorite_phrases (List[str]): List of user's favorite phrases
        settings (Dict[str, Any]): User settings and preferences
        usage_stats (Dict[str, Any]): Usage statistics tracking
        created_at (str): Profile creation timestamp
        last_updated (str): Last update timestamp
    
    Sample Usage:
        # Create a new profile
        profile = UserProfile(user_id="user123", username="John Doe", email="john@example.com")
        
        # Add favorite phrases
        profile.add_favorite_phrase("Hello World")
        profile.add_favorite_phrase("Good Morning")
        
        # Update settings
        profile.update_settings({"theme": "dark", "language": "en"})
        
        # Track usage
        profile.track_usage("eye_tracking", 1)
        profile.track_usage("phrase_selection", 5)
        
        # Save to JSON
        profile.save_to_json("user_profile.json")
        
        # Load from JSON
        loaded_profile = UserProfile.load_from_json("user_profile.json")
        
        # Get profile summary
        summary = profile.get_profile_summary()
        print(summary)
    """
    
    def __init__(self, user_id: str, username: str, email: str):
        """
        Initialize a new UserProfile.
        
        Args:
            user_id (str): Unique identifier for the user
            username (str): User's name
            email (str): User's email address
            
        Raises:
            ValueError: If any parameter is empty or invalid
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if not username or not isinstance(username, str):
            raise ValueError("username must be a non-empty string")
        if not email or not isinstance(email, str):
            raise ValueError("email must be a non-empty string")
        
        self.user_id = user_id
        self.username = username
        self.email = email
        self.favorite_phrases: List[str] = []
        self.settings: Dict[str, Any] = {
            "theme": "light",
            "language": "en",
            "notifications": True,
            "auto_save": True
        }
        self.usage_stats: Dict[str, Any] = {}
        self.created_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
    
    def add_favorite_phrase(self, phrase: str) -> bool:
        """
        Add a phrase to the user's favorite phrases list.
        
        Args:
            phrase (str): The phrase to add
            
        Returns:
            bool: True if phrase was added, False if it already exists
            
        Raises:
            ValueError: If phrase is empty or not a string
        """
        try:
            if not phrase or not isinstance(phrase, str):
                raise ValueError("Phrase must be a non-empty string")
            
            phrase = phrase.strip()
            if phrase in self.favorite_phrases:
                return False
            
            self.favorite_phrases.append(phrase)
            self._update_timestamp()
            return True
        except ValueError as e:
            print(f"Error adding phrase: {e}")
            return False
    
    def remove_favorite_phrase(self, phrase: str) -> bool:
        """
        Remove a phrase from the user's favorite phrases list.
        
        Args:
            phrase (str): The phrase to remove
            
        Returns:
            bool: True if phrase was removed, False if not found
        """
        try:
            if phrase in self.favorite_phrases:
                self.favorite_phrases.remove(phrase)
                self._update_timestamp()
                return True
            return False
        except Exception as e:
            print(f"Error removing phrase: {e}")
            return False
    
    def get_favorite_phrases(self) -> List[str]:
        """
        Get a copy of the favorite phrases list.
        
        Returns:
            List[str]: Copy of favorite phrases
        """
        return self.favorite_phrases.copy()
    
    def update_settings(self, new_settings: Dict[str, Any]) -> bool:
        """
        Update user settings with new values.
        
        Args:
            new_settings (Dict[str, Any]): Dictionary of settings to update
            
        Returns:
            bool: True if settings were updated successfully
            
        Raises:
            ValueError: If new_settings is not a dictionary
        """
        try:
            if not isinstance(new_settings, dict):
                raise ValueError("Settings must be a dictionary")
            
            self.settings.update(new_settings)
            self._update_timestamp()
            return True
        except ValueError as e:
            print(f"Error updating settings: {e}")
            return False
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get a copy of the current settings.
        
        Returns:
            Dict[str, Any]: Copy of user settings
        """
        return self.settings.copy()
    
    def track_usage(self, action: str, count: int = 1) -> bool:
        """
        Track usage statistics for a specific action.
        
        Args:
            action (str): The action being tracked
            count (int): Number of times the action occurred (default: 1)
            
        Returns:
            bool: True if tracking was successful
            
        Raises:
            ValueError: If action is invalid or count is negative
        """
        try:
            if not action or not isinstance(action, str):
                raise ValueError("Action must be a non-empty string")
            if not isinstance(count, int) or count < 0:
                raise ValueError("Count must be a non-negative integer")
            
            if action in self.usage_stats:
                self.usage_stats[action] += count
            else:
                self.usage_stats[action] = count
            
            self._update_timestamp()
            return True
        except ValueError as e:
            print(f"Error tracking usage: {e}")
            return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get a copy of the usage statistics.
        
        Returns:
            Dict[str, Any]: Copy of usage statistics
        """
        return self.usage_stats.copy()
    
    def get_profile_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of the user profile.
        
        Returns:
            Dict[str, Any]: Dictionary containing profile summary
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "favorite_phrases_count": len(self.favorite_phrases),
            "favorite_phrases": self.favorite_phrases.copy(),
            "settings": self.settings.copy(),
            "usage_stats": self.usage_stats.copy(),
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    def save_to_json(self, filepath: str) -> bool:
        """
        Save the user profile to a JSON file.
        
        Args:
            filepath (str): Path where the JSON file will be saved
            
        Returns:
            bool: True if save was successful
            
        Raises:
            IOError: If file cannot be written
            ValueError: If filepath is invalid
        """
        try:
            if not filepath or not isinstance(filepath, str):
                raise ValueError("Filepath must be a non-empty string")
            
            profile_data = {
                "user_id": self.user_id,
                "username": self.username,
                "email": self.email,
                "favorite_phrases": self.favorite_phrases,
                "settings": self.settings,
                "usage_stats": self.usage_stats,
                "created_at": self.created_at,
                "last_updated": self.last_updated
            }
            
            with open(filepath, 'w') as f:
                json.dump(profile_data, f, indent=2)
            
            return True
        except (IOError, OSError) as e:
            print(f"Error saving profile to {filepath}: {e}")
            return False
        except ValueError as e:
            print(f"Invalid input: {e}")
            return False
    
    @staticmethod
    def load_from_json(filepath: str) -> Optional['UserProfile']:
        """
        Load a user profile from a JSON file.
        
        Args:
            filepath (str): Path to the JSON file to load
            
        Returns:
            UserProfile: Loaded profile object, or None if loading failed
            
        Raises:
            FileNotFoundError: If the file does not exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        try:
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Validate required fields
            required_fields = ['user_id', 'username', 'email']
            if not all(field in data for field in required_fields):
                raise ValueError("Missing required fields in JSON")
            
            # Create profile instance
            profile = UserProfile(
                user_id=data['user_id'],
                username=data['username'],
                email=data['email']
            )
            
            # Restore data
            profile.favorite_phrases = data.get('favorite_phrases', [])
            profile.settings = data.get('settings', profile.settings)
            profile.usage_stats = data.get('usage_stats', {})
            profile.created_at = data.get('created_at', profile.created_at)
            profile.last_updated = data.get('last_updated', profile.last_updated)
            
            return profile
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {filepath}: {e}")
            return None
        except ValueError as e:
            print(f"Validation error: {e}")
            return None
    
    def _update_timestamp(self) -> None:
        """
        Update the last_updated timestamp to current time.
        
        This is an internal method called whenever the profile is modified.
        """
        self.last_updated = datetime.now().isoformat()
    
    def __str__(self) -> str:
        """
        Return a string representation of the user profile.
        
        Returns:
            str: Profile information as a formatted string
        """
        return (f"UserProfile(user_id={self.user_id}, username={self.username}, "
                f"email={self.email}, phrases={len(self.favorite_phrases)})")
    
    def __repr__(self) -> str:
        """
        Return a detailed string representation of the user profile.
        
        Returns:
            str: Detailed profile information
        """
        return self.__str__()


if __name__ == "__main__":
    # Example usage and testing
    print("=== UserProfile Example Usage ===")
    
    # Create a new profile
    profile = UserProfile(
        user_id="user_001",
        username="Alice Johnson",
        email="alice@example.com"
    )
    print(f"Created profile: {profile}")
    
    # Add favorite phrases
    profile.add_favorite_phrase("Hello World")
    profile.add_favorite_phrase("Good Morning")
    profile.add_favorite_phrase("Thank You")
    print(f"Added favorite phrases: {profile.get_favorite_phrases()}")
    
    # Update settings
    profile.update_settings({"theme": "dark", "language": "es"})
    print(f"Updated settings: {profile.get_settings()}")
    
    # Track usage
    profile.track_usage("eye_tracking", 1)
    profile.track_usage("phrase_selection", 5)
    profile.track_usage("eye_tracking", 3)
    print(f"Usage stats: {profile.get_usage_stats()}")
    
    # Get profile summary
    print("\nProfile Summary:")
    import pprint
    pprint.pprint(profile.get_profile_summary())
    
    # Save to JSON
    profile.save_to_json("example_profile.json")
    print("\nProfile saved to 'example_profile.json'")
    
    # Load from JSON
    loaded_profile = UserProfile.load_from_json("example_profile.json")
    if loaded_profile:
        print(f"Profile loaded: {loaded_profile}")
        print(f"Loaded phrases: {loaded_profile.get_favorite_phrases()}")
