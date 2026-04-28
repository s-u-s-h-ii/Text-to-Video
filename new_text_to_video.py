import os
import torch
from diffusers import DiffusionPipeline
from gtts import gTTS
import moviepy.editor as mp

base_dir = "C:/Users/ysush/OneDrive/Desktop/text__to__video"
text = 'A space war against aliens. The aliens looks like intelligent species. The moon got destroyed. Aliens summons black-hole which is bigger than the sun'
prompt_sentences = text.split('.')


# Initialize the Diffusion Pipeline
pipe = DiffusionPipeline.from_pretrained(
    "playgroundai/playground-v2-1024px-aesthetic",
    torch_dtype=torch.float16,
    variant="fp16"
).to("cuda")

# Create directories to store generated files
image_dir = os.path.join(base_dir, "images")
audio_dir = os.path.join(base_dir, "audio")
short_video_dir = os.path.join(base_dir, "short_videos")
final_video_dir = os.path.join(base_dir, "final_video")
os.makedirs(image_dir, exist_ok=True)
os.makedirs(audio_dir, exist_ok=True)
os.makedirs(short_video_dir, exist_ok=True)
os.makedirs(final_video_dir, exist_ok=True)

# Generate images and corresponding audio for each sentence
for i, sentence in enumerate(prompt_sentences):
    # Generate image
    image = pipe(sentence).images[0]
    image_path = os.path.join(image_dir, f"image_{i}.png")
    image.save(image_path)

    # Convert text to speech
    tts = gTTS(sentence)
    audio_path = os.path.join(audio_dir, f"audio_{i}.mp3")
    tts.save(audio_path)

# Convert each image to a short video clip
for i in range(len(prompt_sentences)):
    image_path = os.path.join(image_dir, f"image_{i}.png")
    video_clip_path = os.path.join(short_video_dir, f"video_{i}.mp4")

    # Create a short video clip from the image
    clip = mp.ImageClip(image_path, duration=2)  # Adjust duration as needed
    clip.write_videofile(video_clip_path, fps=24)

# Combine images with audio into a video
video_clips = []
for i in range(len(prompt_sentences)):
    video_clip_path = os.path.join(short_video_dir, f"video_{i}.mp4")
    audio_path = os.path.join(audio_dir, f"audio_{i}.mp3")
    video_clip = mp.VideoFileClip(video_clip_path)
    audio_clip = mp.AudioFileClip(audio_path)
    video_clip = video_clip.set_audio(audio_clip)
    video_clips.append(video_clip)

final_video = mp.concatenate_videoclips(video_clips, method="compose")
final_video_path = os.path.join(final_video_dir, "final_video.mp4")
final_video.write_videofile(final_video_path, codec="libx264", fps=24)

print(f"Saved final video to {final_video_path}")