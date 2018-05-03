""" Forecasting toolbox for DustBust
"""

import cosmological_analysis as ca
import angular_spectrum_estimation as ase
from algebra import multi_comp_sep, comp_sep, W_dBdB, W_dB, _mm, _mtmm
import separation_recipies as sr
import numpy as np
import pylab as pl
import healpy as hp

def xForecast(components, instrument, invN, d_fgs, estimator=''):
   """ Run xForecast or CMB4cast using the provided
       instrumental specifications and input foregrounds 
       maps 

    Parameters
    ----------
    ### TODO
    ### CLEAN THE FOLLOWING TEXT
    A_ev: function or list
        The evaluator of the mixing matrix. It takes a float or an array as
        argument and returns the mixing matrix, a ndarray with shape
        `(..., n_freq, n_comp)`
        If list, the i-th entry is the evaluator of the i-th patch.
    d_fgs: ndarray
        The data vector. Shape `(n_freq, n_stokes, n_pix)`.
    invN: ndarray or None
        The inverse noise matrix. Shape `(..., n_freq, n_freq)`.
    estimator: power spectrum estimator to be chosen among ...... 

    Returns
    -------
    xFres:  
    """

    ### TODO [DAVIDE]
    ### COMPUTE and LOAD s_cmb with corresponding power spectra 

    ###############################################################################
    # 0. Prepare noise-free "data sets"
    d_obs = d_fgs.T + CMB().evaluate(instrument.Frequencies)*s_cmb[...,np.newaxis]
    
    ###############################################################################
    # 1. Component separation using the noise-free data sets
    # grab the max-L spectra parameters with the associated error bars
    #  < S_spec > = −tr [(N^-1 − P)(dˆpdˆtp + Np)]
    # P = N^-1 - N^-1 A (AtNinvA) A^t N^-1
    A_ev, A_dB_ev, comp_of_param, params = sr._build_A_evaluators(
        components, instrument)
    x0 = np.array([x for c in components for x in c.defaults])
    
    if nside == 0:
        res = comp_sep(A_ev, d_obs, invN, A_dB_ev, comp_of_param, x0,
                       options=dict(disp=True))
    else:
        patch_ids = hp.ud_grade(np.arange(hp.nside2npix(nside)),
                                hp.npix2nside(d_obs.shape[-1]))
        res = multi_comp_sep(A_ev, d_obs, invN, patch_ids, x0)
    res.params = params
    res.s = res.s.T
    A_maxL = A_ev( res.params )
    A_dB_maxL = A_dB_ev( res.params )
    ### TODO [JOSQUIN]
    ### build mixing matrix object and call diff_diff()
    ### and remove _build_A_evaluators
    A_dBdB_maxL =

    ###############################################################################
    # 2. Estimate noise after component separation
    ### TO DO [DAVIDE]
    ### A^T N_ell^-1 A
    Cl_noise = sr.Cl_noise_builder( instrument, A_maxL )

    ###############################################################################
    # 3. Compute spectra of the input foregrounds maps
    ### TO DO: which size for Cl_fgs??? N_spec != 1 ? 
    N_freqs = data.shape[0]
    for f_1 in range(N_freqs):
        for f_2 in range(N_freqs):
            if f_2 >= f_1:
                # we only take the BB spectra, for ell >= 2
                # this form should be able to handle binned spectra as well
                Cl_loc, ell = ase.TEB_spectra( d_fgs[f_1,:,:], IQU_map_2=d_fgs[f_2,:,:], estimator=estimator )[2]
                if f_1 == 0 and f_2 == 0:
                    Cl_fgs = np.zeros((N_spec, N_freqs, N_freqs, len(Cl_loc)))
                Cl_fgs[f_1,f_2,:] = Cl_loc*1.0
            else:
                # symmetrization of the Cl_fgs matrix
                Cl_fgs[f_1,f_2,:] = Cl_fgs[f_2,f_1,:]
    assert len(Cl_fid) == len(ell)

    ###############################################################################
    # 4. Estimate the statistical and systematic foregrounds residuals 

    ### find ind_cmb, the dimension of the CMB component
    ### TO DO [DAVIDE]
    ### add this list to the MixingMatrix class
    ind_cmb = [type(c).__name__ for c in MixingMatrix].index('CMB')
    W_maxL = W(A_maxL, invN=invN)[...,ind_cmb,:]
    W_dB_maxL = W_dB(A_maxL, A_dB_maxL, comp_of_param, invN=invN)[...,ind_cmb,:]
    W_dBdB_maxL = W_dBdB(A_maxL, A_dB_maxL, A_dBdB_maxL, comp_of_param, invN=invN)[...,ind_cmb,:]
    
    ### TODO: check if arrow is necessary [JOSQUIN]
    V_maxL = np.einsum('ij,ij...->...', res.Sigma, W_dBdB_maxL )
    
    # elementary quantities defined in Stompor, Errard, Poletti (2016)
    Cl_xF = {}
    Cl_xF['yy'] = _mtmm(W_maxL, Cl_fgs, W_maxL)
    Cl_xF['YY'] = _mtmm(W_dB_maxL, Cl_fgs, W_maxL)
    Cl_xF['yz'] = _mtmm(W_maxL, Cl_fgs, V_maxL)
    Cl_xF['Yy'] = _mtmm(W_dB_maxL, Cl_fgs, W_maxL)
    Cl_xF['Yz'] = _mtmm(W_dB_maxL, Cl_fgs, V_maxL)
    Cl_xF['zY'] = _mtmm(V_maxL, Cl_fgs, W_dB_maxL)
    Cl_xF['zy'] = _mtmm(V_maxL, Cl_fgs, W_maxL)
    Cl_xF['yY'] = _mtmm(W_maxL , Cl_fgs, W_dB_maxL)
    # bias and statistical foregrounds residuals
    Cl_xF['bias'] = Cl_xF['yy'] + Cl_xF['yz'] + Cl_xF['zy']
    YSY =  _mm(res.Sigma, Cl_xF['YY'])
    Cl_xF['stat'] = np.trace( YSY )
    Cl_xF['var'] = 2*(_mtmm(Cl_xF['yY'], res.Sigma, Cl_xF['Yy'] ) + Cl_xF['stat']** 2)

    ###############################################################################
    # 5. Plug into the cosmological likelihood
    assert Cl_fid.shape == Cl_xF['yy']
    ## 5.1. data 
    E = np.diag(Cl_fid['BB'] + YSY + Cl_xF['yy'] + Cl_xF['zy'] + Cl_xF['yz'])
    ## 5.2. modeling
    def cosmo_likelihood( r_ ):
        Cl_BB_model = Cl_fid['BlBl']*A_L + Cl_fid['BuBu']*r_/r_fid + Cl_noise

        U_inv = _mm(res.Sigma_inv, np.sum((2*ell+1)*Cl_xF['YY']/Cl_BB_model))
        U = np.linalg.inv( U_inv ) 
        
        term_0 = (2*ell+1)*(1.0 - (1.0/Cl_BB_model)*np.trace(_mm(U, Cl_xF['YY'])))
        term_1 = ((2*ell+1)/Cl_BB_model)*np.trace(_mm(res.Sigma,Cl_xF['YY']))
        trCinvC_1 = np.sum( Cl_fid['BB']/Cl_BB_model*term_0 + term_1 )
        
        trCinvC_2 = 0.0
        for i in range(len(ell)):
            for j in range(len(ell)):
                trCinvC_2 += ((2*ell[i]+1)/Cl_BB_model[i])*((2*ell_v[j]+1)/Cl_BB_model[j])*\
                       np.trace(_mm(_mm(U, Cl_xF['YY'][:,:,j]), _mm(res.Sigma, Cl_xF['YY'][:,:,i])))
       
        trCinvEC_1 = np.sum( ((2*ell+1)/Cl_BB_model)*(Cl_xF['yy'] + Cl_xF['zy'] + Cl_xF['yz']) )
       
        trCinvEC_2 = 0.0
        for i in range(len(ell)):
            for j in range(len(ell)):
                trCinvEC_2 += ((2*ell[i]+1)/Cl_BB_model[i])*((2*ell_v[j]+1)/Cl_BB_model[j])*\
                       np.trace( U.dot(Cl_xF['YY'][:,:,j].dot(res.Sigma.dot(Cl_xF['YY'][:,:,i]))))

        trCE = trCinvC_1 - trCinvC_2 + trCinvEC_1 - trCinvEC_2
        D = np.diag( Cl )
        logL = fsky*( trCE + logdetC ) 
        

    ### TODO [JOSQUIN]
    ###  minimization, gridding, sigma(r)
    ### r_fit = ....

    def sigma_r_computation_from_logL(r_loc):
        THRESHOLD = 1.00
        # THRESHOLD = 2.30 when two fitted parameters
        delta = np.abs( cosmo_likelihood(r_loc) - cosmo_likelihood(r_fit) - THRESHOLD )
        return delta


    ### TODO [DAVIDE]        
    ### outputs

    '''
    # analytical derivative of logL also available in xForecast .... 

    # optimization of logL wrt. r
    # estimation of the Hessian (analytical Fisher?) at the peak 
    # possibility of returning a gridded likelihood?
    '''

    ###############################################################################
    # 6. Produce figures
    '''
	# angular power spectrum showing theoretical Cl / noise per freq band / noise after comp sep / stat and sys residuals
	# the emcee panels for the spectral parameters fit
	# the profile cosmological likelihood (if it has been gridded)
    '''
