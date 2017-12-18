from astrometry.util.fits import *

'''
Parse the PHAT young & old cluster catalogs sent by Nelson, 2017-12-15
'''

def convert(f, name):
    hdr = f.readline()
    f.readline()
    
    T = fits_table()
    T.name = []
    T.ra = []
    T.dec = []
    T.comment = []
    T.mag = []
    T.velocity = []
    T.metallicity = []
    
    for line in f.readlines():
        words = line.split()
        T.name.append(words[0])
        T.ra.append(float(words[1]))
        T.dec.append(float(words[2]))
        cc = ' '.join(words[3:])
        T.comment.append(cc)
    
        # strip off quotation marks
        cc = cc.replace('"','')
        words = cc.split(',')
        #print('words', words)
        T.mag.append(float(words[0].strip()))
        if len(words) >= 2:
            v = float(words[1].replace('km/s', '').strip())
        else:
            v = 0.
        T.velocity.append(v)
        if len(words) >= 3:
            z = float(words[2].strip())
        else:
            z = 0
        T.metallicity.append(z)
    T.to_np_arrays()
    T.mag = T.mag.astype(np.float32)
    T.metallicity = T.metallicity.astype(np.float32)
    T.velocity = T.velocity.astype(np.float32)
    T.writeto('%s.fits' % name)



f = open('young_phat_clusters', 'rb')
convert(f, 'phat-clusters-young')

f = open('old_phat_clusters', 'rb')
convert(f, 'phat-clusters-old')
