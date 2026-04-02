# Image Processing Tool - Implementation Summary

## ✅ What Was Implemented

### New Tool: `process_image`
A powerful image processing tool that allows the LLM agent to manipulate images using ImageMagick commands via your Windmill API.

## 🎯 How It Works

### User Workflow:
1. **User attaches an image** to their Discord message
2. **User requests processing**: "Make this smaller", "Rotate this 90 degrees", "Make it black and white", etc.
3. **Bot extracts image URL** from Discord attachment automatically
4. **LLM decides to use tool** based on user request
5. **Tool sends to Windmill API**:
   - Image URL
   - Generated ImageMagick command
6. **Windmill processes image** using ImageMagick
7. **Returns base64-encoded** processed image
8. **Bot displays result** as a Discord attachment

### Example Interactions:

```
User: [attaches photo.jpg] Can you make this 50% smaller?
Bot: [analyzes request]
Bot: [calls process_image(url, "-resize 50%")]
Bot: Here's your resized image! [sends processed_photo.png]

User: [attaches image] Rotate this 90 degrees and convert to grayscale
Bot: [calls process_image(url, "-rotate 90 -colorspace Gray")]
Bot: I've rotated and converted your image to grayscale! [sends result]

User: [attaches picture] Add a sepia effect
Bot: [calls process_image(url, "-sepia-tone 80%")]
Bot: Here's your image with a sepia tone effect applied! [sends result]
```

## 📁 Files Created/Modified

### New Files:
- **`llm/tools/image_processor.py`** - Image processing tool implementation
  - Integrates with Windmill API
  - Validates image URLs
  - Handles base64 encoding/decoding
  - Supports all ImageMagick commands

### Modified Files:
- **`llm/llm.py`**:
  - Added `_extract_image_urls()` - Extracts URLs from Discord attachments
  - Added `_parse_processed_images()` - Parses base64 images from tool responses
  - Updated `_send_response()` - Sends images as Discord attachments
  - Updated `on_message()` - Includes image URLs in LLM context

- **`llm/README.md`**:
  - Added image processing setup instructions
  - Added example usage
  - Updated environment variables section

- **`llm/tools/README.md`**:
  - Added comprehensive image processor documentation
  - Included example ImageMagick commands
  - Added Windmill workflow example

## ⚙️ Setup Required

### 1. Windmill API Endpoint

Create a Windmill workflow at endpoint `process_image` that:

**Accepts:**
```json
{
  "image_url": "https://cdn.discordapp.com/attachments/.../image.jpg",
  "magick_command": "-resize 50%"
}
```

**Returns:**
```json
{
  "image_base64": "iVBORw0KGgoAAAANS...",
  "format": "png"
}
```

### 2. Windmill Workflow Example (TypeScript):

```typescript
export async function main(image_url: string, magick_command: string) {
  // Download image
  const response = await fetch(image_url);
  const imageBuffer = await response.arrayBuffer();
  
  // Save to temp file
  const inputPath = '/tmp/input.jpg';
  await Deno.writeFile(inputPath, new Uint8Array(imageBuffer));
  
  // Execute ImageMagick
  const outputPath = '/tmp/output.png';
  const cmd = `magick ${inputPath} ${magick_command} ${outputPath}`;
  await Deno.run({ cmd: cmd.split(' ') }).status();
  
  // Read and encode result
  const outputBuffer = await Deno.readFile(outputPath);
  const base64 = btoa(String.fromCharCode(...new Uint8Array(outputBuffer)));
  
  return {
    image_base64: base64,
    format: 'png'
  };
}
```

### 3. Environment Variables:

```bash
# Already configured (from rec cog)
WINDMILL_TOKEN=your_windmill_token
WINDMILL_URL=https://your-windmill-instance.com
```

### 4. Restart the bot

The tool will auto-load when the cog starts.

## 🎨 Supported ImageMagick Operations

### Resize & Transform:
- `"-resize 50%"` - Resize to 50%
- `"-resize 800x600"` - Resize to specific dimensions
- `"-rotate 90"` - Rotate 90 degrees
- `"-flip"` - Flip vertically
- `"-flop"` - Flip horizontally

### Effects:
- `"-sepia-tone 80%"` - Sepia effect
- `"-blur 0x8"` - Blur
- `"-sharpen 0x1"` - Sharpen
- `"-negate"` - Invert colors
- `"-normalize"` - Auto-adjust brightness/contrast
- `"-edge 1"` - Edge detection

### Color:
- `"-colorspace Gray"` - Grayscale
- `"-modulate 100,150,100"` - Increase saturation

### Format & Quality:
- `"-quality 85 -format jpg"` - Convert to JPEG
- `"-format png"` - Convert to PNG

### Borders & Frames:
- `"-border 10x10 -bordercolor black"` - Add border

### Combinations:
- `"-resize 50% -rotate 90 -quality 85"`

## 🔧 Technical Details

### Image Flow:
```
Discord Message (with attachment)
    ↓
Extract image URL from attachment
    ↓
Add to LLM context: "Attached images: https://..."
    ↓
LLM calls: process_image(url, command)
    ↓
Tool → Windmill API
    ↓
Windmill: Download → Process → Encode
    ↓
Return: [IMAGE_PROCESSED]Format: png\nData: base64...[/IMAGE_PROCESSED]
    ↓
Bot parses special markers
    ↓
Decode base64 → Create Discord.File
    ↓
Send to channel with attachment
```

### Special Response Format:
The tool returns a specially formatted string that the bot parses:
```
[IMAGE_PROCESSED]
Format: png
Data: iVBORw0KGgoAAAANSUhEUgAA...
[/IMAGE_PROCESSED]
```

This allows the LLM to include explanatory text while the bot handles the actual image display.

## 🧪 Testing

### Test Command:
```
.llmtest I have an image at https://example.com/photo.jpg - can you resize it to 50%?
```

### Test with Attachment:
1. Upload an image in Discord
2. In the same message, type: "Make this smaller"
3. Bot should process and return the resized image

### Check Tool Status:
```
.llmstatus
```
Should show: `• process_image`

### View Tool Details:
```
.llmtools
```
Should show full parameters for `process_image`

## 🚀 Usage Tips

### Natural Language:
Users can request image processing naturally:
- "Make this image smaller"
- "Rotate the photo 90 degrees"
- "Convert this to black and white"
- "Add a sepia effect"
- "Blur this image"
- "Make it sharper"

The LLM translates these to appropriate ImageMagick commands automatically!

### Multiple Images:
If user attaches multiple images, they're all extracted and the LLM can process any of them by referencing the URL.

### URL Support:
Users can also provide image URLs directly:
- "Process this image: https://example.com/photo.jpg - make it 800px wide"

## ⚠️ Important Notes

1. **Windmill Timeout**: Image processing set to 60-second timeout (configurable)
2. **File Size**: Discord attachment limit is 8MB (or 25MB with Nitro)
3. **Supported Formats**: JPEG, PNG, GIF, WebP (depends on ImageMagick installation)
4. **Security**: Image URLs are validated before processing
5. **Error Handling**: Clear error messages if Windmill API fails

## 📊 Benefits

✅ **Natural Interface**: Users don't need to know ImageMagick syntax
✅ **Automatic**: Bot handles all URL extraction and image sending
✅ **Flexible**: Supports any ImageMagick command
✅ **Integrated**: Works seamlessly with other tools
✅ **Scalable**: Processing handled by Windmill, not Discord bot

---

Your bot can now process images automatically! 🎉
