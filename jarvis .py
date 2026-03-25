import pyttsx3
import datetime
import speech_recognition as sr
import webbrowser as wb
import os
import subprocess
import json
from dataclasses import dataclass
from enum import Enum
import time
import pygame
import random
from mutagen import File
from typing import List, Optional
import urllib.parse

class MessageType(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class ChatMessage:
    content: str
    type: MessageType
    timestamp: datetime.datetime

@dataclass
class MusicTrack:
    title: str
    path: str
    duration: float

class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self.current_track = None
        self.playlist = []
        self.is_playing = False
        self.is_paused = False

    def load_music_directory(self, directory: str) -> List[MusicTrack]:
        music_files = []
        supported_formats = ('.mp3', '.wav', '.ogg')
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(supported_formats):
                    file_path = os.path.join(root, file)
                    try:
                        audio = File(file_path)
                        duration = audio.info.length if audio else 0
                        track = MusicTrack(
                            title=os.path.splitext(file)[0],
                            path=file_path,
                            duration=duration
                        )
                        music_files.append(track)
                    except Exception:
                        continue
        return music_files

    def play(self, track: MusicTrack):
        try:
            pygame.mixer.music.load(track.path)
            pygame.mixer.music.play()
            self.current_track = track
            self.is_playing = True
            self.is_paused = False
            return True
        except Exception as e:
            print(f"Error playing track: {e}")
            return False

    def pause(self):
        if self.is_playing and not self.is_paused:
            pygame.mixer.music.pause()
            self.is_paused = True
            return True
        return False

    def resume(self):
        if self.is_playing and self.is_paused:
            pygame.mixer.music.unpause()
            self.is_paused = False
            return True
        return False

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.current_track = None

    def set_volume(self, volume: float):
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

class JarvisAssistant:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 3000
        self.recognizer.pause_threshold = 0.8
        self.recognizer.phrase_threshold = 0.3
        
        self.voice_enabled = True
        self.chat_history = []
        
        # Initialize application paths
        self.app_paths = {
            'excel': r'C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE',
            'word': r'C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE',
            'powerpoint': r'C:\Program Files\Microsoft Office\root\Office16\POWERPNT.EXE',
            'notepad': r'notepad.exe',
            'calculator': r'calc.exe',
            'paint': r'mspaint.exe',
            'wuthering waves': r'E:\Wuthering Waves\launcher.exe',
            'unity': r'C:\Program Files\Unity Hub\Unity Hub.exe',
        }
        
        # Initialize folder paths
        self.folder_paths = {
            'documents': os.path.expanduser('~/Documents'),
            'downloads': os.path.expanduser('~/Downloads'),
            'pictures': os.path.expanduser('~/Pictures'),
            'music': os.path.expanduser('~/Music'),
            'videos': os.path.expanduser('~/Videos'),
            'desktop': os.path.expanduser('~/Desktop'),
            'c': 'C:\\',
            'd': 'D:\\',
            'e': 'E:\\',
            'movies': 'D:\\Movies',
            'games': 'D:\\Games',
            'work': 'D:\\Work',
            'projects': 'D:\\Projects'
        }
        
        self.music_player = MusicPlayer()
        self.music_library = []
        self.load_music_library()

    def search_folder(self, folder_name: str, root_paths: List[str], max_depth: int = 3) -> Optional[str]:
        folder_name = folder_name.lower()
        found_paths = []
        start_time = time.time()
        timeout = 10  # Maximum search time in seconds
        
        def is_system_folder(path: str) -> bool:
            system_folders = {'$recycle.bin', 'system volume information', 'windows', 
                            'programdata', 'program files', 'program files (x86)'}
            return any(sf in path.lower() for sf in system_folders)
        
        for root_path in root_paths:
            if not os.path.exists(root_path):
                continue
                
            try:
                for root, dirs, _ in os.walk(root_path, topdown=True):
                    # Check timeout
                    if time.time() - start_time > timeout:
                        print("Search timeout reached")
                        break
                    
                    # Skip system folders and hidden folders
                    dirs[:] = [d for d in dirs if not d.startswith('.') and not is_system_folder(d)]
                    
                    # Check search depth
                    current_depth = root[len(root_path):].count(os.sep)
                    if current_depth >= max_depth:
                        dirs.clear()  # Stop going deeper
                        continue
                    
                    # Check each directory in current path
                    for dir_name in dirs:
                        if time.time() - start_time > timeout:
                            break
                            
                        if folder_name in dir_name.lower():
                            full_path = os.path.join(root, dir_name)
                            found_paths.append(full_path)
                            # If we found an exact match, return immediately
                            if dir_name.lower() == folder_name:
                                return full_path
                    
            except (PermissionError, OSError):
                continue  # Skip inaccessible directories
        
        # If no exact match found, return the closest match
        if found_paths:
            return min(found_paths, key=lambda x: (
                abs(len(os.path.basename(x)) - len(folder_name)),
                len(x)
            ))
        return None

    def load_music_library(self):
        music_folder = self.folder_paths['music']
        if os.path.exists(music_folder):
            self.music_library.extend(self.music_player.load_music_directory(music_folder))

    def speak(self, audio: str, message_type: MessageType = MessageType.ASSISTANT):
        message = ChatMessage(audio, message_type, datetime.datetime.now())
        self.chat_history.append(message)
        print(f"Jarvis: {audio}")
        
        if self.voice_enabled:
            self.engine.say(audio)
            self.engine.runAndWait()

    def take_command(self):
        with sr.Microphone() as source:
            print("Listening...")
            try:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5)
                print("Processing...")
                command = self.recognizer.recognize_google(audio, language="en-US")
                print(f"You said: {command}")
                return command.lower()
            except (sr.UnknownValueError, sr.RequestError, sr.WaitTimeoutError) as e:
                print("Sorry, I didn't catch that. Please try again.")
                return "Try Again"
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                return "Try Again"

    def verify_command(self, command: str) -> str:
        if command not in ["Try Again", ""]:
            self.speak(f"I heard: {command}. Is this correct? Say yes or no.", MessageType.SYSTEM)
            max_attempts = 3
            for _ in range(max_attempts):
                verification = self.take_command()
                if verification == "Try Again":
                    continue
                
                if any(word in verification for word in ['yes', 'yeah', 'correct', 'right']):
                    return command
                elif any(word in verification for word in ['no', 'nope', 'wrong', 'incorrect']):
                    self.speak("Please repeat your command.", MessageType.SYSTEM)
                    return self.take_command()
                else:
                    self.speak("Please say yes or no.", MessageType.SYSTEM)
                
        # If we've exhausted all attempts
            self.speak("Having trouble understanding. Please try again.", MessageType.SYSTEM)
            return "Try Again"
        return command

    def google_search(self, query: str) -> bool:
        try:
            # Clean and encode the search query
            cleaned_query = query.replace("search for", "").replace("search", "").strip()
            encoded_query = urllib.parse.quote(cleaned_query)
            
            # Construct the search URL
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            # Open in default browser
            wb.open(search_url)
            self.speak(f"Searching Google for: {cleaned_query}")
            return True
        except Exception as e:
            self.speak(f"Error performing Google search: {str(e)}", MessageType.SYSTEM)
            return False

    def open_folder(self, folder_name: str) -> bool:
        try:
            # First check predefined paths
            if folder_name.lower() in self.folder_paths:
                path = self.folder_paths[folder_name.lower()]
                if os.path.exists(path):
                    subprocess.Popen(['explorer.exe', path])
                    self.speak(f"Opening folder: {folder_name}")
                    return True
            
            # Define root paths to search
            root_paths = [
                os.path.expanduser('~'),  # User's home directory first
                'C:\\',
                'D:\\',
                'E:\\',
                os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files')),
                os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)')),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop'),
                os.path.join(os.environ.get('USERPROFILE', ''), 'Documents')
            ]
            
            self.speak(f"Searching for folder: {folder_name}")
            found_path = self.search_folder(folder_name, root_paths)
            
            if found_path:
                subprocess.Popen(['explorer.exe', found_path])
                self.speak(f"Opening folder: {os.path.basename(found_path)}")
                return True
            else:
                self.speak(f"Sorry, I couldn't find any folder matching '{folder_name}'")
                return False
                
        except Exception as e:
            self.speak(f"Error opening folder: {str(e)}", MessageType.SYSTEM)
            return False

    def open_application(self, app_name: str) -> bool:
        try:
            app_name = app_name.lower()
            if app_name in self.app_paths:
                path = self.app_paths[app_name]
                try:
                    subprocess.run([path], shell=True, check=True)
                    self.speak(f"Opening {app_name}")
                    return True
                except subprocess.CalledProcessError:
                    self.speak(f"Error: {app_name} requires elevated permissions to open.")
                    return False
            else:
                # Try to find the application in the default Windows locations
                paths = [
                    f"C:\\Program Files\\{app_name}.exe",
                    f"C:\\Program Files (x86)\\{app_name}.exe",
                    f"D:\\Program Files\\{app_name}.exe",
                    f"D:\\Program Files (x86)\\{app_name}.exe",
                    f"{app_name}.exe"
                ]
                for path in paths:
                    if os.path.exists(path):
                        try:
                            subprocess.run([path], shell=True, check=True)
                            self.speak(f"Opening {app_name}")
                            return True
                        except subprocess.CalledProcessError:
                            self.speak(f"Error: {app_name} requires elevated permissions to open.")
                            return False
                self.speak(f"Application '{app_name}' not found in C, D, or E drives.")
                return False
        except Exception as e:
            self.speak(f"Error opening application: {e}", MessageType.SYSTEM)
            return False

    def list_folders(self):
        self.speak("Available folders:")
        print("\nPredefined folders:")
        for folder_name, path in self.folder_paths.items():
            if os.path.exists(path):
                print(f"- {folder_name}: {path}")
        print("\nYou can also access any folder in C or D E drive using 'open folder [folder_name]'")

    def process_command(self, command: str) -> bool:
        if not command or command == "Try Again":
            return True

        # Google search command
        if "search for" in command or command.startswith("search "):
            return self.google_search(command)

        # List folders command
        if "list folders" in command:
            self.list_folders()
            return True

        # Basic commands
        if "time" in command:
            self.speak(datetime.datetime.now().strftime("The time is %I:%M %p"))
        
        elif "date" in command:
            self.speak(datetime.datetime.now().strftime("Today is %B %d, %Y"))
        
        elif "youtube" in command:
            wb.open("https://youtube.com")
            self.speak("Opening YouTube")
        
        elif "google" in command:
            wb.open("https://google.com")
            self.speak("Opening Google")
        
        elif "gmail" in command:
            wb.open("https://gmail.com")
            self.speak("Opening Gmail")

        elif "amazon" in command:
            wb.open("https://amazon.com")
            self.speak("Opening amazon")
        
        elif "javascript" in command:
            wb.open("https://javascript.com")
            self.speak("Opening javascript")
        
        elif "chatgpt" in command:
            wb.open("https://chatgpt.com")
            self.speak("Opening chatgpt")

        # Folder and application commands
        elif "open folder" in command:
            folder_name = command.replace("open folder", "").strip()
            if not self.open_folder(folder_name):
                self.speak(f"Sorry, I couldn't find folder '{folder_name}' in the system.")
        
        elif "open" in command:
            app_name = command.replace("open", "").strip()
            if not self.open_application(app_name):
                self.speak(f"Sorry, I couldn't find application '{app_name}' in the system.")

        # Music commands
        elif "play music" in command or "play song" in command:
            if not self.music_library:
                self.speak("No music files found in the music library")
                return True
            
            if "play song" in command:
                song_name = command.replace("play song", "").strip()
                matching_tracks = [
                    track for track in self.music_library 
                    if song_name in track.title.lower()
                ]
                if matching_tracks:
                    track = matching_tracks[0]
                    if self.music_player.play(track):
                        self.speak(f"Playing {track.title}")
                    else:
                        self.speak("Error playing the track")
                else:
                    self.speak(f"No songs found matching '{song_name}'")
            else:
                track = random.choice(self.music_library)
                if self.music_player.play(track):
                    self.speak(f"Playing random song: {track.title}")
                else:
                    self.speak("Error playing music")

        elif any(word in command for word in ["pause music", "pause song", "pause"]):
            if self.music_player.is_playing:
                self.music_player.pause()
                self.speak("Music paused")
            else:
                self.speak("No music is currently playing")

        elif any(word in command for word in ["resume music", "resume song", "resume", "continue music", "continue song", "continue"]):
            if self.music_player.is_paused:
                self.music_player.resume()
                self.speak("Resuming music")
            elif self.music_player.is_playing and not self.music_player.is_paused:
                self.speak("Music is already playing")
            else:
                self.speak("No music is paused")

        elif "stop" in command:
            if self.music_player.is_playing:
                self.music_player.stop()
                self.speak("Stopped playing music")
            else:
                self.speak("No music is playing")

        elif "volume" in command:
            try:
                volume = int(''.join(filter(str.isdigit, command)))
                if 0 <= volume <= 100:
                    self.music_player.set_volume(volume / 100)
                    self.speak(f"Volume set to {volume}%")
                else:
                    self.speak("Please specify a volume between 0 and 100")
            except ValueError:
                self.speak("Please specify a valid volume level")

        elif "what's playing" in command:
            if self.music_player.current_track:
                self.speak(f"Currently playing: {self.music_player.current_track.title}")
            else:
                self.speak("No music is currently playing")

        elif "list songs" in command:
            if self.music_library:
                self.speak("Here are the songs in your library:")
                for i, track in enumerate(self.music_library, 1):
                    print(f"{i}. {track.title}")
            else:
                self.speak("No songs found in the music library")

        elif "toggle voice" in command:
            self.voice_enabled = not self.voice_enabled
            self.speak(f"Voice output {('enabled' if self.voice_enabled else 'disabled')}")

        elif "chat history" in command:
            for msg in self.chat_history:
                print(f"[{msg.timestamp.strftime('%H:%M:%S')}] {msg.type.value.capitalize()}: {msg.content}")

        # Exit command
        elif "goodbye" in command or "offline" in command or "exit" in command:
            if self.music_player.is_playing:
                self.music_player.stop()
            self.speak("Goodbye!")
            return False
            
        return True

    def run(self):
        hour = datetime.datetime.now().hour
        greeting = "Good Morning!" if hour < 12 else "Good Afternoon!" if hour < 18 else "Good Evening!"
        self.speak(f"{greeting} I am JARVIS. How can I help you?")
        
        print("\nAvailable commands:")
        print("\nSearch Commands:")
        print("- 'search for [query]' or 'search [query]' - Search Google")
        
        print("\nFolder Commands:")
        print("- 'open folder [folder name]' - Open folder in system")
        print("- 'list folders' - Show all available folders")
        
        print("\nMusic Commands:")
        print("- 'play music' - Play random song")
        print("- 'play song [song name]' - Play specific song")
        print("- 'pause' - Pause music")
        print("- 'resume' - Resume music")
        print("- 'stop' - Stop music")
        print("- 'volume [0-100]' - Set volume")
        print("- 'what's playing' - Show current song")
        print("- 'list songs' - Show all songs")
        
        print("\nApplication Commands:")
        print("- 'open [app name]' - Open application")
        print("- 'youtube' - Open YouTube")
        print("- 'google' - Open Google")
        print("- 'gmail' - Open Gmail")
        
        print("\nOther Commands:")
        print("- 'time' - Get current time")
        print("- 'date' - Get current date")
        print("- 'toggle voice' - Enable/disable voice output")
        print("- 'chat history' - Show conversation history")
        print("- 'goodbye' or 'exit' - Exit")
             
        while True:
            print("\nOptions: [Enter] for voice command, [Type] your command, or 'exit' to quit")
            command = input("[Text Input] > ").strip().lower()
            if not command:
                command = self.take_command()
                command = self.verify_command(command)
            
            if not self.process_command(command):
                break

if __name__ == "__main__":
    jarvis = JarvisAssistant()
    jarvis.run()