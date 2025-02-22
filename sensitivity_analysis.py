from model import *
from agents import *
from mesa.batchrunner import BatchRunner, FixedBatchRunner
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
from SALib.sample import saltelli
from SALib.analyze import sobol
import pandas as pd
plt.style.use('ggplot')

# Local Sensitivity Analysis

problem = {
    'num_vars': 10,
    'names': ['team_size', 'rationality_of_agents', 'jail_time', 'prob_of_prosecution', 'memory_size',
              'cost_complain', 'penalty_citizen_prosecution',
              'jail_cost_factor','citizen_complain_memory_discount_factor', 'bribe_amount'],
    'bounds': [[5, 25], [0.01, 0.99], [1, 15], [0.01, 0.99], [2, 20], [0.3, 60], [0, 20], [0.3, 35], [0, 35], [0, 5]]
}

integer_vars = ['team_size', 'jail_time', 'memory_size']
# Set the repetitions, the amount of steps, and the amount of distinct values per variable
replicates = 20
max_steps = 130
distinct_samples = 15

# Set the outputs
model_reporters = { "Bribing": lambda m: sum([1 for cop in m.schedule_Cop.agents if cop.action == cop.possible_actions(0)]),
             "NoBribing": lambda m: sum([1 for cop in m.schedule_Cop.agents if cop.action == cop.possible_actions(1)])}

data = {}

for i, var in enumerate(problem['names']):
    # Get the bounds for this variable and get <distinct_samples> samples within this space (uniform)
    samples = np.linspace(*problem['bounds'][i], num=distinct_samples)
    # Some parameters should have integer values. We change
    # the code to acommodate for this and sample only integers.
    if var in integer_vars:
        samples = np.linspace(*problem['bounds'][i], num=distinct_samples, dtype=int)

    batch = BatchRunner(Corruption,
                        max_steps=max_steps,
                        iterations=replicates,
                        variable_parameters={var: samples},
                        model_reporters=model_reporters,
                        display_progress=True)

    batch.run_all()
    data[var] = batch.get_model_vars_dataframe()


def plot_param_var_conf(df, var, param, i):
    """
    Helper function for plot_all_vars. Plots the individual parameter vs
    variables passed.
    Args:
        ax: the axis to plot to
        df: dataframe that holds the data to be plotted
        var: variables to be taken from the dataframe
        param: which output variable to plot
    """
    x = df.groupby(var).mean().reset_index()[var]
    y = df.groupby(var).mean()[param]

    replicates = df.groupby(var)[param].count()
    err = (1.96 * df.groupby(var)[param].std()) / np.sqrt(replicates)

    plt.plot(x, y, c='k')
    plt.plot(x, y, '.', color='blue')
    plt.fill_between(x, y - err, y + err, alpha=0.5)

    plt.xlabel(var)
    plt.ylabel(param)

def plot_all_vars(df, param):
    """
    Plots the parameters passed vs each of the output variables.
    Args:
        df: dataframe that holds all data
        param: the parameter to be plotted
    """

    for i, var in enumerate(problem['names']):
        plt.figure(figsize=(6.5,3.5))
        plot_param_var_conf(data[var], var, param, i)


for param in ('Bribing', 'NoBribing'):
    plot_all_vars(data, param)
    plt.savefig('downloads/LSA.png', dpi = 300)
    plt.show()

#RUNNING THE MODEL USING BASELINE VALUES MULTIPLE TIMES TO GET THE DISTRIBUTION OF THE OUTPUTS
def model_baseline_output(team_size, rationality_of_agents, jail_time, prob_of_prosecution, memory_size, cost_complain, penalty_citizen_prosecution, jail_cost_factor, citizen_complain_memory_discount_factor, bribe_amount, max_steps, model_reporters):

    data_fixed = {}

    batch_fixed = FixedBatchRunner(Corruption,
                                   parameters_list=[
                                       {'team_size': team_size, 'rationality_of_agents': rationality_of_agents,
                                        'jail_time': jail_time,
                                        'prob_of_prosecution': prob_of_prosecution,
                                        'memory_size':memory_size,'cost_complain':cost_complain,
                                        'penalty_citizen_prosecution':penalty_citizen_prosecution,
                                        'jail_cost_factor':jail_cost_factor,
                                        'citizen_complain_memory_discount_factor':citizen_complain_memory_discount_factor,
                                        'bribe_amount':bribe_amount}],
                                   iterations=120,
                                   max_steps=max_steps,
                                   model_reporters=model_reporters)
    batch_fixed.run_all()

    data_fixed = batch_fixed.get_model_vars_dataframe()
    amount_bribe = data_fixed["Bribing"].values
    amount_nobribe = data_fixed["NoBribing"].values

    def plot_dist(data, data_name):
        fig = plt.figure(figsize=(12, 5))
        ax = fig.add_subplot(111)

        # Plot the histogram
        ax.hist(
        data,
        bins=20,
        density=True,
        label="Histogram from samples",
        zorder=5,
        edgecolor="k",
        alpha=0.5,
        )

        kde = sm.nonparametric.KDEUnivariate(data)

        kde.fit()  # Estimate the densities

        # Plot the KDE as fitted using the default arguments
        ax.plot(kde.support, kde.density, lw=3, label="KDE from samples", zorder=10)

        ax.set_ylabel('Density')
        ax.set_xlabel(data_name)
        ax.legend(loc="best")
        ax.grid(True, zorder=-5)
        plt.show()

    def qq_plot(data, data_name):
        sm.qqplot(data, line='s',marker='.', markerfacecolor='k', markeredgecolor='k', alpha=0.3)
        plt.title(data_name)
        plt.show()

    for data, label in [(amount_bribe,"amount_bribe"),(amount_nobribe, "amount_nobribe")]:
        plot_dist(data, label)
        qq_plot(data, label)

model_baseline_output(team_size=10, rationality_of_agents=0.75, jail_time=4, prob_of_prosecution=0.7,
                      memory_size=10,  cost_complain=3, penalty_citizen_prosecution=5, jail_cost_factor=5,
                      citizen_complain_memory_discount_factor=3, bribe_amount=50, max_steps=max_steps,
                      model_reporters=model_reporters)

#Global Sensitivity Analysis
# replicates_global = 10
# max_steps_global = 130
# distinct_samples_global = 10
#
# # We get all our samples here
# param_values = saltelli.sample(problem, distinct_samples_global, calc_second_order = False)
#
# batch_global = BatchRunner(Corruption,
#                     max_steps=max_steps_global,
#                     variable_parameters={name:[] for name in problem['names']},
#                     model_reporters=model_reporters)
#
# count = 0
# data_global = pd.DataFrame(index=range(replicates_global*len(param_values)),
#                                 columns= problem['names'])
# data_global['Run'], data_global['Bribe'], data_global['NoBribe'] = None, None, None
#
# for i in range(replicates_global):
#     for vals in param_values:
#         # Change parameters that should be integers
#         vals = list(vals)
#         vals[2] = int(vals[2])
#         # Transform to dict with parameter names and their values
#         variable_parameters = {}
#         for name, val in zip(problem['names'], vals):
#             variable_parameters[name] = val
#
#         batch_global.run_iteration(variable_parameters, tuple(vals), count)
#         iteration_data = batch_global.get_model_vars_dataframe().iloc[count]
#         iteration_data['Run'] = count
#         data_global.iloc[count, 0:6] = vals
#         data_global.iloc[count, 6:9] = iteration_data
#         count += 1
#
#         print(f'{count / (len(param_values) * (replicates_global)) * 100:.2f}% done')
#
# Si_bribe = sobol.analyze(problem, data_global['Bribe'].values, calc_second_order = False, print_to_console=True)
# Si_nobribe = sobol.analyze(problem, data_global['NoBribe'].values, calc_second_order = False, print_to_console=True)
#
# def plot_index(s, params, i, title=''):
#     """
#     Creates a plot for Sobol sensitivity analysis that shows the contributions
#     of each parameter to the global sensitivity.
#
#     Args:
#         s (dict): dictionary {'S#': dict, 'S#_conf': dict} of dicts that hold
#             the values for a set of parameters
#         params (list): the parameters taken from s
#         i (str): string that indicates what order the sensitivity is.
#         title (str): title for the plot
#     """
#
#
#     indices = s['S' + i]
#     errors = s['S' + i + '_conf']
#     plt.figure()
#
#     l = len(indices)
#
#     plt.title(title)
#     plt.ylim([-0.2, len(indices) - 1 + 0.2])
#     plt.yticks(range(l), params)
#     plt.errorbar(indices, range(l), xerr=errors, linestyle='None', marker='o')
#     plt.axvline(0, c='k')
#
#
# for Si in (Si_bribe, Si_nobribe):
#     # First order
#     plot_index(Si, problem['names'], '1', 'First order sensitivity')
#     plt.show()
#
#     # Total order
#     plot_index(Si, problem['names'], 'T', 'Total order sensitivity')
#     plt.show()