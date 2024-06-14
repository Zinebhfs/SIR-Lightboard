import os
import pyautogui

def screenshot():
    # Capture the screenshot
    screenshot = pyautogui.screenshot()
    # Convert the image to RGB mode
    screenshot = screenshot.convert('RGB')
    # Define the file path
    screenshot_path = os.path.join(os.getcwd(), "screenshot.jpg")
    # Save the screenshot
    screenshot.save(screenshot_path)
    print(f"Screenshot taken and saved as {screenshot_path}")

if __name__ == "__main__":
    screenshot()

