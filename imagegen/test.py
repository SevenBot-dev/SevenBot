import colorsys 
from PIL import Image, ImageDraw

images = []

width = 400
center = width // 2
color_1 = (0, 0, 0)
max_radius = int(center * 1.5)
step = 8
for i in range(0, width,4):
	im = Image.new('RGB', (width, 1))
	draw = ImageDraw.Draw(im)
	for j in range(0, width):
		#print(j,i,width,(j+i)%width,colorsys.hsv_to_rgb(int((j+i)%width/float(width))%1,1,1))
		draw.rectangle((width-j,0,0,1), fill=tuple(map(lambda c: int(c*255),colorsys.hsv_to_rgb(((j+i)%width/float(width))%1,1,1))))
	 
	images.append(im)
		
images[0].save('./pillow_imagedraw.gif',
save_all=True, append_images=images[1:], optimize=False, duration=40, loop=0)