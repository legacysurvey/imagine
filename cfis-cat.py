import numpy as np
from astrometry.util.fits import *
from argparse import ArgumentParser

def main():
    parser = ArgumentParser()
    parser.add_argument('infns', nargs='+')
    opts = parser.parse_args()

    Nap = 20
    cols = (('cfis_id x_image y_image ra dec ' +
             'u_mag_auto u_magerr_auto u_mag_best u_magerr_best').split() +
            ['u_mag_aper_%i' % i for i in range(Nap)] +
            ['u_magerr_aper_%i' % i for i in range(Nap)] +
            ('u_a_world u_erra_world u_b_world u_errb_world ' +
             'u_theta_j2000 u_errtheta_j2000 ' +
             'u_isoarea_image ' +
             'u_mu_max u_flux_radius ' +
             'u_flags ' +
             'u_mag_apauto u_magerr_apauto u_mag_cog u_magerr_cog ' +
             'u_mag_2arc u_magerr_2arc u_iq ' +
             'u_maglim_2arc u_maglim_apauto u_maglim_cog').split() +

            ('r_mag_auto r_magerr_auto r_mag_best r_magerr_best').split() +
            ['r_mag_aper_%i' % i for i in range(Nap)] +
            ['r_magerr_aper_%i' % i for i in range(Nap)] +
            ('r_a_world r_erra_world r_b_world r_errb_world ' +
             'r_theta_j2000 r_errtheta_j2000 ' +
             'r_isoarea_image ' +
             'r_mu_max r_flux_radius ' +
             'r_flags ' +
             'r_mag_apauto r_magerr_apauto r_mag_cog r_magerr_cog ' +
             'r_mag_2arc r_magerr_2arc r_iq ' +
             'r_maglim_2arc r_maglim_apauto r_maglim_cog').split())

    print(len(cols), 'columns')

    tmap = dict(cfis_id = np.int64,
                ra = np.float64,
                dec = np.float64,
                u_isoarea_image = np.int16,
                r_isoarea_image = np.int16,
                u_flags = np.int32,
                r_flags = np.int32,
                )
    types = [tmap.get(c, np.float32) for c in cols]

    for infn in opts.infns:
        print()
        print('Reading', infn)
        outfn = infn.replace('.cat', '.fits')
        T = text_table_fields(infn, #skiplines=133,
                              headerline=' '.join(cols),
                              coltypes=types)
        N = len(T)
        for k in ['u_mag_aper', 'u_magerr_aper', 'r_mag_aper', 'r_magerr_aper']:
            A = np.zeros((N, Nap), np.float32)
            for i in range(Nap):
                ki = k + '_%i'%i
                v = T.get(ki)
                A[:,i] = v
                T.delete_column(ki)
            T.set(k, A)
        #T.about()
        T.writeto(outfn)
        print('Wrote', len(T), 'to', outfn)

if __name__ == '__main__':
    main()
    
