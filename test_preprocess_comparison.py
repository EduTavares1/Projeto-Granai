import os
import sys
import cv2
import pytesseract

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

image_path = "Comprovantes testes/comp01.jpg"

if not os.path.exists(image_path):
    print(f"Error: {image_path} not found.")
    sys.exit(1)

# Load image
img = cv2.imread(image_path)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# Preprocessing Option 1: Just raw grayscale
txt_gray = pytesseract.image_to_string(gray, lang="por", config="--oem 3 --psm 4")

# Preprocessing Option 2: Gaussian Blur + Otsu Thresholding
blurred_otsu = cv2.GaussianBlur(gray, (5, 5), 0)
_, otsu = cv2.threshold(blurred_otsu, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
txt_otsu = pytesseract.image_to_string(otsu, lang="por", config="--oem 3 --psm 4")

# Preprocessing Option 3: Gaussian Blur + Adaptive Thresholding with larger block size (e.g. 41)
blurred_adapt = cv2.GaussianBlur(gray, (3, 3), 0)
adapt = cv2.adaptiveThreshold(
    blurred_adapt, 
    255, 
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    cv2.THRESH_BINARY, 
    31, 
    2
)
txt_adapt = pytesseract.image_to_string(adapt, lang="por", config="--oem 3 --psm 4")

# Print comparisons
print("==================================================")
print("Option 1: Raw Grayscale OCR Result")
print("==================================================")
print(txt_gray[:500])
print("\n" + "="*50)
print("Option 2: Gaussian Blur + Otsu Thresholding OCR Result")
print("==================================================")
print(txt_otsu[:500])
print("\n" + "="*50)
print("Option 3: Adaptive Thresholding (BlockSize 31) OCR Result")
print("==================================================")
print(txt_adapt[:500])
print("==================================================")

# Save the options to inspect visually
os.makedirs("debug_vision_test", exist_ok=True)
cv2.imwrite("debug_vision_test/opt1_gray.jpg", gray)
cv2.imwrite("debug_vision_test/opt2_otsu.jpg", otsu)
cv2.imwrite("debug_vision_test/opt3_adapt.jpg", adapt)
print("Saved comparison images to 'debug_vision_test/' folder.")
