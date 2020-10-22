import sys
from astropy.coordinates import SkyCoord

import mysql_db as mdb

__author__ = "Natasha Hurley-Walker"


class Source:
    def __init__(self, name, pos, flux, alpha, beta):
        self.name = name
        self.pos = pos
        self.flux = flux
        self.alpha = alpha
        self.beta = beta
    
    def __repr__(self):
        return "{0} {1} {2} {3} {4} {5}".format(src.name, src.pos.ra.deg, src.pos.dec.deg, src.flux, src.alpha, src.beta)


def insert_src(src, cur):
    print(src)

    cur.execute("""
    INSERT INTO sources
    (source, RAJ2000, DecJ2000, flux, alpha, beta)
    VALUES
    (%s, %s, %s, %s, %s, %s);
    """, (src.name, src.pos.ra.deg, src.pos.dec.deg, src.flux, src.alpha, src.beta))
    return

if __name__ == "__main__":
    conn = mdb.connect()
    cur = conn.cursor()
    
    casa = Source("CasA", SkyCoord("23h23m24.000s   +58d48m54.00s"),  13000., -0.5, 0.0 )
    cyga = Source("CygA", SkyCoord("19h59m28.35663s +40d44m02.0970s"), 9000., -1.0, 0.0 )
    crab = Source("Crab", SkyCoord("05h34m31.94s    +22d00m52.2s"),    1500., -0.5, 0.0 )
    vira = Source("VirA", SkyCoord("12h30m49.42338s +12d23m28.0439s"), 1200., -1.0, 0.0 )
    pica = Source("PicA", SkyCoord("05h19m49.7229s  -45d46m43.853s"),   570., -1.0, 0.0 )
    hera = Source("HerA", SkyCoord("16h51m11.4s     +04d59m20s"),       520., -1.1, 0.0 )
    hyda = Source("HydA", SkyCoord("09h18m05.651s   -12d05m43.99s"),    350., -0.9, 0.0 )

    sources = [casa, cyga, crab, vira, pica, hera, hyda]

    for src in sources:
        insert_src(src, cur)
        conn.commit()
    conn.commit()
    conn.close()
