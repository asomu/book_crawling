from PIL import Image, ImageFilter, ImageOps

def resize_and_center_image(image_path, output_path):
    icon_path = r"C:\Users\asomu\OneDrive\사진\icons.png"
    icon_image = Image.open(icon_path)
    target_image = Image.open(image_path)
    shadowed_image = Image.new('RGBA', target_image.size, (125, 125, 125, 255))
    target_image = target_image.resize((target_image.size[0]-2, target_image.size[1]-2))

    shadowed_image.paste(target_image, (1, 1))
    # 이미지에 그림자를 추가합니다.
    # ret_image.save(output_path)
    # shadowed_image.show()

    x,y = shadowed_image.size
    yres = int((1000-y)/2)
    xres = int((1000-x)/2)
    icon_x = xres + x - 20
    icon_y = yres + y - 20
    blank_image = Image.new("RGBA", (1000, 1000), (255, 255, 255, 255))
    blank_image.paste(shadowed_image, (xres, yres))
    ret_image = blank_image.convert('RGB')
    # ret_image.show()
    ret_image.paste(icon_image, (icon_x, icon_y))
    # icon_image.show()
    ret_image.show()

def _resize_img(src):
    img = Image.open(src)
    resized_img = img.resize(
        (int(img.size[0]*900/img.size[1]), 900), Image.LANCZOS)
    resized_img.save("output.jpg")

if __name__ == "__main__":
    image_path = r"C:\Users\asomu\OneDrive\사진\9791168411685.jpg"
    output_path = "output.jpg"
    # resize_and_center_image(image_path, output_path)
    _resize_img(image_path)
