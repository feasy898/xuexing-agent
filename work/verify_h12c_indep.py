import math, itertools
from math import comb, perm, factorial
from fractions import Fraction
res = {}

res['h_coup_001'] = 4*3
res['h_coup_002'] = sum(1 for a in range(1,6) for b in range(1,6) if a!=b and (a+b)%2==0)
cnt=0
for p in itertools.permutations(range(6),3):
    if p[0]!=0 and p[1]<p[2]: cnt+=1
res['h_coup_003']=cnt
res['h_coua_001']=3*2*2
cnt=0
for p in itertools.permutations('abcde'):
    if p[2]=='a' and p[0]!='b' and p[4]!='b': cnt+=1
res['h_coua_002']=cnt
cnt=0
people='abcdef'
for act1 in itertools.combinations(people,2):
    rem1=[x for x in people if x not in act1]
    for act2 in itertools.combinations(rem1,2):
        act3=tuple(x for x in rem1 if x not in act2)
        for assign in [(act1,act2,act3),(act1,act3,act2),(act2,act1,act3),(act2,act3,act1),(act3,act1,act2),(act3,act2,act1)]:
            if not any('a' in g and 'b' in g for g in assign): cnt+=1
res['h_coua_003']=cnt
res['h_perm_001']=perm(5,3)+perm(5,2)
res['h_perm_002']=sum(1 for p in itertools.permutations(range(1,6),3) if p[0]>p[1]>p[2])
res['h_perm_003']=sum(1 for p in itertools.permutations(range(1,6)) if p[0]!=1 and p[-1]!=5)
res['h_comb_001']=comb(8,2)-comb(6,2)
res['h_comb_002']=comb(7,3)-comb(4,3)
res['h_comb_003']=comb(5,3)*comb(4,2)-comb(4,2)*comb(3,1)
res['h_cmpp_001']=[n for n in range(1,30) if comb(n,5)==comb(n,7)]
res['h_cmpp_002']=comb(100,98)
s=sum(k*comb(4,k) for k in range(1,5))
res['h_cmpp_003']=(s, 4*2**3, 4*2**4, 2**4)
res['h_pcap_001']=factorial(5)*2
res['h_pcap_002']=factorial(4)*comb(5,2)
res['h_pcap_003']=sum(1 for p in itertools.permutations('abcde') if p[0]!='a' and p[-1]!='b')
res['h_bith_001']=comb(5,2)
k=[k for k in range(7) if 6-2*k==0][0]
res['h_bith_002']=comb(6,k)*(-1)**k
n=6
kk=[k for k in range(n+1) if (n-k)/2-k==0][0]
res['h_bith_003']=comb(n,kk)*(-1/2)**kk
res['h_bicp_003']=sum(comb(i,2) for i in range(2,11))
res['h_biap_001']=1+5*0.01
kk=[k for k in range(10) if 18-3*k==3][0]
res['h_biap_002']=comb(9,kk)*(-1)**kk
pe=Fraction(1,16)*(comb(4,0)+comb(4,2)+comb(4,4))
res['h_biap_003']=(float(pe), Fraction(1,2))
res['h_conp_001']=Fraction(4,7)
res['h_conp_002']=Fraction(3,10)*Fraction(2,9)
P_D2=Fraction(4,10); P_D1D2=Fraction(4,10)*Fraction(3,9)
res['h_conp_003']=P_D1D2/P_D2
res['h_evti_002']=1-0.2*0.4
res['h_evti_003']=0.5+0.6-0.5*0.6
res['h_totp_001']=Fraction(3,5)*Fraction(1,2)+Fraction(2,5)*Fraction(1,3)
res['h_totp_002']=Fraction(40,100)*Fraction(2,100)+Fraction(35,100)*Fraction(1,100)+Fraction(25,100)*Fraction(3,100)
pr=Fraction(4,5)*Fraction(1,2)+Fraction(1,5)*Fraction(1,4)
res['h_totp_003']=(Fraction(4,5)*Fraction(1,2))/pr
res['h_rvds_003']=(Fraction(comb(2,2),10),Fraction(comb(3,1)*comb(2,1),10),Fraction(comb(3,2),10))
res['h_rvmn_001']=1*0.2+2*0.5+3*0.3
res['h_rvmn_002']=5*0.8
res['h_rvmn_003']=Fraction(sum(k*k for k in range(1,6)),15)
res['h_rvva_001']=0.4*0.6
res['h_rvva_002']=10*0.5*0.5
res['h_rvva_003']=(3*2+5, 9*9)
res['h_berb_001']=comb(3,2)*0.6**2*0.4
res['h_berb_002']=(12*(1-Fraction(8,12)), 12/(1-Fraction(8,12)))
res['h_berb_003']=sorted(set(Fraction(k,100) for k in range(1,100) if comb(4,1)*Fraction(k,100)*(1-Fraction(k,100))**3==comb(4,3)*Fraction(k,100)**3*(1-Fraction(k,100))))
res['h_hypg_002']=3*Fraction(5,50)
res['h_hypg_003']=Fraction(comb(6,2)*comb(4,2),comb(10,4))
res['h_nrmd_003']=(1-0.6826)/2
res['h_corc_003']=6/math.sqrt(18*8)
xs=[1,2,3,4,5]; ys=[2,3,5,6,7]
xb=sum(xs)/5; yb=sum(ys)/5
b1=sum((x-xb)*(y-yb) for x,y in zip(xs,ys))/sum((x-xb)**2 for x in xs)
b0=yb-b1*xb
res['h_lnrg_003']=(b1,b0)
res['h_resr_003']=1-Fraction(20,100)
res['h_ctta_002']=Fraction(60,200)
res['h_ctta_003']=(Fraction(30,300),)
a,bb,c2,d2=80,20,40,60
N=a+bb+c2+d2
chi=N*(a*d2-bb*c2)**2/((a+bb)*(c2+d2)*(a+c2)*(bb+d2))
res['h_chit_003']=float(chi)
for k,v in res.items(): print(k, v)
