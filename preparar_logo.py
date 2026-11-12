"""12/11: prepara un logo de competición que manda Marcos (JPG/PNG con fondo blanco) para las fotos:
quita el fondo, pasa a blanco lo negro/gris oscuro (va sobre un estadio de noche) y lo guarda en
publicaciones/media/escudos/liga-<id>-hd.png. Uso: python preparar_logo.py origen.jpg destino.png <id>"""
import sys
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
def preparar(src, dst, lid, umbral_oscuro=105):
    im=Image.open(src).convert("RGB"); a=np.array(im).astype(int)
    blanco=(a.min(axis=2)>215)
    from scipy import ndimage
    etiq,_=ndimage.label(blanco)
    bordes=set(np.unique(np.concatenate([etiq[0],etiq[-1],etiq[:,0],etiq[:,-1]])))-{0}
    fondo=np.isin(etiq,list(bordes))
    cerca=np.array(Image.fromarray((fondo*255).astype("uint8")).filter(ImageFilter.MaxFilter(5)))>0
    alfa=np.full(fondo.shape,255); alfa[fondo]=0
    borde=cerca & ~fondo
    alfa[borde]=np.clip((255-a.min(axis=2)[borde])*3,0,255)
    rgb=a.copy()
    gris_osc=(a.max(axis=2)<umbral_oscuro)|((a.max(axis=2)-a.min(axis=2)<50)&(a.max(axis=2)<130))
    rgb[gris_osc]=[244,244,244]
    rgb[borde & (a.max(axis=2)<160)]=[244,244,244]
    if lid==61:   # fuera el patrocinador (amarillo)
        amar=(a[:,:,0]>190)&(a[:,:,1]>130)&(a[:,:,2]<110)
        filas=np.where(amar.any(axis=1))[0]
        if len(filas): alfa[max(0,filas.min()-10):,:]=0
    if lid in (39, 525, 2):   # huecos blancos/grises por dentro del dibujo, también transparentes
        claro=(a.max(axis=2)-a.min(axis=2)<18)&(a.min(axis=2)>175)
        alfa[claro]=0
    res=Image.fromarray(np.dstack([rgb,alfa]).astype("uint8"),"RGBA"); res=res.crop(res.getbbox())
    res.thumbnail((800,800),Image.LANCZOS); res.save(dst,optimize=True); return res.size
if __name__=="__main__": print(preparar(sys.argv[1],sys.argv[2],int(sys.argv[3])))
