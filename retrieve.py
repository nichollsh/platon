import eos_reader
import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate
from transit_depth_calculator import TransitDepthCalculator
import emcee
from fit_info import FitInfo

class Retriever:
    def __init__(self):
        self.metallicities = [0.1, 1, 5, 10, 30, 50, 100, 1000]
        self.abundances = []
        for m in self.metallicities:
            m_str = str(m).replace('.', 'p')
            filename = "EOS/eos_{0}Xsolar_cond.dat".format(m_str)
            abundances = eos_reader.get_abundances(filename)
            self.abundances.append(abundances)


    def interp_metallicity_grid(self, metallicity):
        result = dict()
        for key in self.abundances[0]:
            grids = [self.abundances[i][key] for i in range(len(self.abundances))]
            interpolator = scipy.interpolate.interp1d(self.metallicities, grids, axis=0)
            result[key] = interpolator(metallicity)
        return result

    def ln_prob(self, params, calculator, fit_info, measured_depths, measured_errors, low_P=0.1, high_P=2e5, num_P=400, max_scatt_factor=10):
        if not fit_info.within_limits(params): return -np.inf
        params_dict = fit_info.interpret_param_array(params)

        R = params_dict["R"]
        T = params_dict["T"]
        metallicity = 10.0**params_dict["logZ"]
        scatt_factor = 10.0**params_dict["log_scatt_factor"]
        cloudtop_P = 10.0**params_dict["log_cloudtop_P"]
        
        if metallicity < np.min(self.metallicities) or metallicity > np.max(self.metallicities): return -np.inf
        if T <= np.min(calculator.T_grid) or T >= np.max(calculator.T_grid): return -np.inf
        if cloudtop_P <= low_P or cloudtop_P >= high_P: return -np.inf

        P_profile = np.logspace(np.log10(low_P), np.log10(high_P), num_P)
        T_profile = np.ones(num_P) * T
        abundances = self.interp_metallicity_grid(metallicity)
        
        wavelengths, calculated_depths = calculator.compute_depths(R, P_profile, T_profile, abundances, scattering_factor=scatt_factor, cloudtop_pressure=cloudtop_P)                
        result = -0.5 * np.sum((calculated_depths - measured_depths)**2/measured_errors**2)
        median_diff = 1e6*np.median(np.abs(calculated_depths - measured_depths))
        '''if median_diff < 30:
            plt.plot(wavelengths, calculated_depths, '.')
            plt.errorbar(wavelengths, measured_depths, yerr=measured_errors, fmt='.')
            plt.show()'''
        print result, median_diff, R/7.1e7, T, metallicity, scatt_factor, cloudtop_P
        return result
    
    def run_emcee(self, wavelength_bins, depths, errors, fit_info, nwalkers=50, nsteps=10000):        
        initial_positions = fit_info.generate_rand_param_arrays(nwalkers)
        calculator = TransitDepthCalculator(fit_info.get("star_radius"), fit_info.get("g"))
        calculator.change_wavelength_bins(wavelength_bins)        
        
        sampler = emcee.EnsembleSampler(nwalkers, fit_info.get_num_fit_params(), self.ln_prob, args=(calculator, fit_info, depths, errors))
        sampler.run_mcmc(initial_positions, nsteps)
        np.save("chain.npy", sampler.chain)
        np.save("lnprob.npy", sampler.lnprob)
        


retriever = Retriever()

#Compile HD209458b data for test run
wavelengths = 1e-6*np.array([1.119, 1.138, 1.157, 1.175, 1.194, 1.213, 1.232, 1.251, 1.270, 1.288, 1.307, 1.326, 1.345, 1.364, 1.383, 1.401, 1.420, 1.439, 1.458, 1.477, 1.496, 1.515, 1.533, 1.552, 1.571, 1.590, 1.609, 1.628])
wavelength_bins = [[w-0.0095e-6, w+0.0095e-6] for w in wavelengths]
depths = 1e-6 * np.array([14512.7, 14546.5, 14566.3, 14523.1, 14528.7, 14549.9, 14571.8, 14538.6, 14522.2, 14538.4, 14535.9, 14604.5, 14685.0, 14779.0, 14752.1, 14788.8, 14705.2, 14701.7, 14677.7, 14695.1, 14722.3, 14641.4, 14676.8, 14666.2, 14642.5, 14594.1, 14530.1, 14642.1])
errors = 1e-6 * np.array([50.6, 35.5, 35.2, 34.6, 34.1, 33.7, 33.5, 33.6, 33.8, 33.7, 33.4, 33.4, 33.5, 33.9, 34.4, 34.5, 34.7, 35.0, 35.4, 35.9, 36.4, 36.6, 37.1, 37.8, 38.6, 39.2, 39.9, 40.8])

R_guess = 9.7e7
T_guess = 1200
metallicity_guess = 1
scatt_factor_guess = 1
cloudtop_P_guess = 1e6

fit_info = FitInfo({'R': R_guess, 'T': T_guess, 'logZ': np.log10(metallicity_guess), 'log_scatt_factor': np.log10(scatt_factor_guess), 'log_cloudtop_P': np.log10(cloudtop_P_guess), 'star_radius': 8.0e8, 'g': 9.311})

fit_info.add_fit_param('R', 0.9*R_guess, 1.1*R_guess, 0, np.inf)
fit_info.add_fit_param('T', 0.5*T_guess, 1.5*T_guess, 0, np.inf)
fit_info.add_fit_param('logZ', -1, 3, -1, 3)
fit_info.add_fit_param('log_cloudtop_P', -1, 6, -np.inf, np.inf)

retriever.run_emcee(wavelength_bins, depths, errors, fit_info)

