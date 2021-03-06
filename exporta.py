# -*- coding: utf-8 -*-
import sys
import re
from pypdf2xml import pdf2xml
from lxml import etree

def split_blocs_alumnes( root ):
    blocs = []
    dades=[d for d in root.findall('.//text')]
    bloc=[]
    estat = 'fent_res'
    for d in dades:
        #estava recolectant i canvi d'alumne
        if estat == 'recolectant' and d.attrib.get('left','')=="87" and d.attrib.get('width','')=="7" and re.match('\d{2}', d.text):
            blocs.append(bloc)
            bloc=[]
        #estava recolectant i s'acaba la pagina
        if estat == 'recolectant' and d.attrib.get('left','')=="87" and d.text == "Signatura del tutor":
            blocs.append(bloc)
            bloc=[]
            estat = 'fent_res'
        #troba un alumne
        if estat == 'fent_res' and d.attrib.get('left','')=="87" and d.attrib.get('width','')=="7" and re.match('\d{2}', d.text):
            estat = 'recolectant'
        if estat == 'recolectant':
            bloc.append(d)
    return blocs

def dades_alumne( bloc_alumne ):
    alumne = {}
    nom_alumne = next( d.text for d in bloc_alumne if d.attrib.get('left','')=="151" )
    alumne['nom'] = nom_alumne
    return alumne

def pilla_elements_ufs( mp_detectat, bloc_alumne ):
    #totes les uf's sota d'aquest MP
    ufs=[]
    elements_per_sota = [ e for e in bloc_alumne if int(e.attrib['top'])>int(mp_detectat.attrib['top']) and e.attrib['left']==mp_detectat.attrib['left'] ]
    nota_raw=None
    uf=None
    for e in elements_per_sota:
        if re.match( 'MP.*', e.text):
            break
        elif re.match( 'UF.*',e.text):
            if uf:
                ufs.append( { 'uf':uf, 'nota_raw':nota_raw } )
            uf=e.text
            s1 = next( n for n in bloc_alumne if n.attrib['top']==e.attrib['top'] and int(n.attrib['left'])>int(e.attrib['left']) )
            nota_raw = s1.text
            try:
                #les R queden separades, les busco.
                s2 = next( n for n in bloc_alumne if n.attrib['top']==s1.attrib['top'] and int(n.attrib['left'])>int(s1.attrib['left']) )
                nota_raw += ( " " + s2.text if ( s2.text.isdigit() or s2.text == "R") else "" )

                mateixa_columna = lambda x, desde: int(x.attrib['left'])-3 <= int(desde.attrib['left']) and int(x.attrib['left'])+3>= int(desde.attrib['left'])
                elements_per_sota = sorted(  [ x for x in bloc_alumne if ( int(x.attrib['top']) >  int( s2.attrib['top'] ) and mateixa_columna( s2, x ) )],
                                             key= lambda x: int(x.attrib['top']) )
                seguent_per_sota = next( x for x in elements_per_sota )
                if seguent_per_sota.text == '10':
                    nota_raw += " 10"
            except StopIteration:
                pass

        else:
            try:
                nota_raw_tmp= next( n.text for n in bloc_alumne if n.attrib['top']==e.attrib['top'] and int(n.attrib['left'])>int(e.attrib['left']) )
                if "TC:" not in nota_raw_tmp:
                    nota_raw = (nota_raw or '') + " " + nota_raw_tmp
            except StopIteration:
                pass
    if uf:
        ufs.append( { 'uf':uf, 'nota_raw':nota_raw } )

    return ufs

def split_blocs_mps( bloc_alumne ):
    mps_detectats = [ d for d in bloc_alumne if re.match( 'MP0\d{2}', d.text ) ]
    mps=[]
    for mp_detectat in mps_detectats:
        ufs = pilla_elements_ufs( mp_detectat, bloc_alumne )
        mps.append( {'nom':mp_detectat.text,
                     'ufs':ufs})
    return mps


def cuina_nota( nota_raw ):
    f0 = re.search( "^-$", nota_raw )
    f1 = re.search( "^- (\d+)$", nota_raw )
    f2 = re.search( "^- (\d+) (A. | *)(\d+)$", nota_raw )
    f4 = re.search( "^- (\d+) (\w+)$", nota_raw )
    if f0:
        nota=""
        hores=""
    elif f1:
        nota=""
        hores=f1.groups()[0]
    elif f2:
        nota=f2.groups()[2]
        hores=f2.groups()[0]
    elif f4:
        nota=f4.groups()[1]
        hores=f4.groups()[0]
    else:
        nota=nota_raw
        hores = None
    return nota, hores

def tracta_fitxer(fitxer, debug_alumne = None):
    s=pdf2xml(open(fitxer,'rb'))
    root = etree.fromstring(s.replace('\n',''))
    for bloc_alumne in split_blocs_alumnes( root ):
        alumne = dades_alumne( bloc_alumne )
        mps=split_blocs_mps( bloc_alumne )
	if debug_alumne:
            if debug_alumne in alumne['nom']:
                return bloc_alumne, mps
        else:
            for mp in mps:
                for uf in mp['ufs']:
                    nota, hores = cuina_nota( uf['nota_raw'] )
                    r = u"{}|{}|{}|{}|{}|{}".format(fitxer.split(".")[0],alumne['nom'], mp['nom'],uf['uf'], nota, hores)
                    print r

fitxers = ['smx1a.pdf','smx1b.pdf','smx1c.pdf','smx2a.pdf','smx2b.pdf',]
print "Grup|Alumne|MP|UF|nota|hores"
for fitxer in fitxers:
    tracta_fitxer(fitxer)
