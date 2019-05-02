
import numpy as np

from phoebe.parameters import *
from phoebe.parameters import dataset as _dataset
import phoebe.dynamics as dynamics
from phoebe.atmospheres import passbands # needed to get choices for 'atm' parameter
from phoebe import u
from phoebe import conf

### NOTE: if creating new parameters, add to the _forbidden_labels list in parameters.py

passbands._init_passbands()  # TODO: move to module import
_atm_choices = list(set([atm for pb in passbands._pbtable.values() for atm in pb['atms']]))

def phoebe(**kwargs):
    """
    Create a <phoebe.parameters.ParameterSet> for compute options for the
    PHOEBE 2 backend.  This is the default built-in backend so no other
    pre-requisites are required.

    When using this backend, please see the
    [list of publications](https://phoebe-project/org/publications) and cite
    the appropriate references.

    See also:
    * <phoebe.frontend.bundle.Bundle.references>

    Generally, this will be used as an input to the kind argument in
    <phoebe.frontend.bundle.Bundle.add_compute>.  If attaching through
    <phoebe.frontend.bundle.Bundle.add_compute>, all `**kwargs` will be
    passed on to set the values as described in the arguments below.  Alternatively,
    see <phoebe.parameters.ParameterSet.set_value> to set/change the values
    after creating the Parameters.

    For example:

    ```py
    b.add_compute('phoebe')
    b.run_compute(kind='phoebe')
    ```

    Note that default bundles (<phoebe.frontend.bundle.Bundle.default_binary>, for example)
    include a set of compute options for the phoebe backend.

    Arguments
    ----------
    * `enabled` (bool, optional): whether to create synthetics in compute/fitting
        run.
    * `dynamics_method` (string, optional): which method to use to determine the
        dynamics of components.
    * `ltte` (bool, optional): whether to correct for light travel time effects.
    * `atm` (string, optional): atmosphere tables
    * `irrad_method` (string, optional): which method to use to handle irradiation.
    * `boosting_method` (string, optional): type of boosting method.
    * `mesh_method` (string, optional): which method to use for discretizing
        the surface.
    * `eclipse_method` (string, optional): which method to use for determinging
        eclipses.
    * `rv_method` (string, optional): which method to use for compute radial
        velocities.

    Returns
    --------
    * (<phoebe.parameters.ParameterSet>): ParameterSet of all newly created
        <phoebe.parameters.Parameter> objects.
    """
    params = []

    params += [BoolParameter(qualifier='enabled', copy_for={'context': 'dataset', 'dataset': '*'}, dataset='_default', value=kwargs.get('enabled', True), description='Whether to create synthetics in compute/fitting run')]

    # DYNAMICS
    params += [ChoiceParameter(qualifier='dynamics_method', value=kwargs.get('dynamics_method', 'keplerian'), choices=['keplerian', 'bs', 'rebound', 'nbody'] if conf.devel else ['keplerian', 'nbody'], description='Which method to use to determine the dynamics of components')]
    params += [BoolParameter(qualifier='ltte', value=kwargs.get('ltte', False), description='Correct for light travel time effects')]

    if conf.devel:
        params += [BoolParameter(visible_if='dynamics_method:nbody', qualifier='gr', value=kwargs.get('gr', False), description='Whether to account for general relativity effects')]
        params += [FloatParameter(visible_if='dynamics_method:nbody', qualifier='stepsize', value=kwargs.get('stepsize', 0.01), default_unit=None, description='stepsize for the N-body integrator')]         # TODO: improve description (and units??)
        params += [ChoiceParameter(visible_if='dynamics_method:nbody', qualifier='integrator', value=kwargs.get('integrator', 'ias15'), choices=['ias15', 'whfast', 'sei', 'leapfrog', 'hermes'], description='Which integrator to use within rebound')]

    # params += [FloatParameter(visible_if='dynamics_method:bs', qualifier='stepsize', value=kwargs.get('stepsize', 0.01), default_unit=None, description='stepsize for the N-body integrator')]         # TODO: improve description (and units??)
    # params += [FloatParameter(visible_if='dynamics_method:bs', qualifier='orbiterror', value=kwargs.get('orbiterror', 1e-20), default_unit=None, description='orbiterror for the N-body integrator')]  # TODO: improve description (and units??)


    # PHYSICS
    # TODO: should either of these be per-dataset... if so: copy_for={'kind': ['rv_dep', 'lc_dep'], 'dataset': '*'}, dataset='_default' and then edit universe.py to pull for the correct dataset (will need to become dataset-dependent dictionary a la ld_func)
    params += [ChoiceParameter(qualifier='irrad_method', value=kwargs.get('irrad_method', 'wilson'), choices=['none', 'wilson', 'horvat'], description='Which method to use to handle all irradiation effects (reflection, redistribution)')]
    params += [ChoiceParameter(qualifier='boosting_method', value=kwargs.get('boosting_method', 'none'), choices=['none', 'linear'], description='Type of boosting method')]

    # TODO: include scattering here? (used to be in lcdep)

    #params += [ChoiceParameter(qualifier='irradiation_alg', value=kwargs.get('irradiation_alg', 'point_source'), choices=['full', 'point_source'], description='Type of irradiation algorithm')]

    # MESH
    # -- these parameters all need to exist per-component --
    # copy_for = {'kind': ['star', 'disk', 'custombody'], 'component': '*'}
    # means that this should exist for each component (since that has a wildcard) which
    # has a kind in [star, disk, custombody]
    # params += [BoolParameter(qualifier='horizon', value=kwargs.get('horizon', False), description='Store horizon for all meshes (except protomeshes)')]
    params += [ChoiceParameter(copy_for={'kind': ['star', 'envelope'], 'component': '*'}, component='_default', qualifier='mesh_method', value=kwargs.get('mesh_method', 'marching'), choices=['marching', 'wd'] if conf.devel else ['marching'], description='Which method to use for discretizing the surface')]
    params += [IntParameter(visible_if='mesh_method:marching', copy_for={'kind': ['star', 'envelope'], 'component': '*'}, component='_default', qualifier='ntriangles', value=kwargs.get('ntriangles', 1500), limits=(100,None), default_unit=u.dimensionless_unscaled, description='Requested number of triangles (won\'t be exact).')]
    params += [ChoiceParameter(visible_if='mesh_method:marching', copy_for={'kind': ['star'], 'component': '*'}, component='_default', qualifier='distortion_method', value=kwargs.get('distortion_method', 'roche'), choices=['roche', 'rotstar', 'sphere'], description='Method to use for distorting stars')]


    if conf.devel:
        # TODO: can we have this computed from ntriangles? - and then do the same for the legacy compute options?
        # NOTE: if removing from developer mode - also need to remove if conf.devel in io.py line ~800
        params += [IntParameter(visible_if='mesh_method:wd', copy_for={'kind': ['star', 'envelope'], 'component': '*'}, component='_default', qualifier='gridsize', value=kwargs.get('gridsize', 60), limits=(10,None), default_unit=u.dimensionless_unscaled, description='Number of meshpoints for WD method')]
    # ------------------------------------------------------

    #params += [ChoiceParameter(qualifier='subdiv_alg', value=kwargs.get('subdiv_alg', 'edge'), choices=['edge'], description='Subdivision algorithm')]
    # params += [IntParameter(qualifier='subdiv_num', value=kwargs.get('subdiv_num', 3), limits=(0,None), description='Number of subdivisions')]



    if conf.devel:
        params += [BoolParameter(qualifier='mesh_offset', value=kwargs.get('mesh_offset', True), description='Whether to adjust the mesh to have the correct surface area (TESTING)')]
        params += [FloatParameter(visible_if='mesh_method:marching', copy_for={'kind': ['star', 'envelope'], 'component': '*'}, component='_default', qualifier='mesh_init_phi', value=kwargs.get('mesh_init_phi', 0.0), default_unit=u.rad, limits=(0,2*np.pi), description='Initial rotation offset for mesh (TESTING)')]

    # DISTORTION


    # ECLIPSE DETECTION
    params += [ChoiceParameter(qualifier='eclipse_method', value=kwargs.get('eclipse_method', 'native'), choices=['only_horizon', 'graham', 'none', 'visible_partial', 'native', 'wd_horizon'] if conf.devel else ['native', 'only_horizon'], description='Type of eclipse algorithm')]
    params += [ChoiceParameter(visible_if='eclipse_method:native', qualifier='horizon_method', value=kwargs.get('horizon_method', 'boolean'), choices=['boolean', 'linear'] if conf.devel else ['boolean'], description='Type of horizon method')]



    # PER-COMPONENT
    params += [ChoiceParameter(copy_for = {'kind': ['star'], 'component': '*'}, component='_default', qualifier='atm', value=kwargs.get('atm', 'ck2004'), choices=_atm_choices, description='Atmosphere table')]

    # PER-DATASET

    # -- these parameters all need to exist per-rvobs or lcobs --
    # copy_for = {'kind': ['rv_dep'], 'component': '*', 'dataset': '*'}
    # means that this should exist for each component/dataset pair with the
    # rv_dep kind
    params += [ChoiceParameter(qualifier='lc_method', copy_for = {'kind': ['lc'], 'dataset': '*'}, dataset='_default', value=kwargs.get('lc_method', 'numerical'), choices=['numerical', 'analytical'] if conf.devel else ['numerical'], description='Method to use for computing LC fluxes')]
    params += [ChoiceParameter(qualifier='fti_method', copy_for = {'kind': ['lc'], 'dataset': '*'}, dataset='_default', value=kwargs.get('fti_method', 'none'), choices=['none', 'oversample'], description='How to handle finite-time integration (when non-zero exptime)')]
    params += [IntParameter(visible_if='fti_method:oversample', qualifier='fti_oversample', copy_for={'kind': ['lc'], 'dataset': '*'}, dataset='_default', value=kwargs.get('fti_oversample', 5), limits=(1,None), default_unit=u.dimensionless_unscaled, description='Number of times to sample per-datapoint for finite-time integration')]

    # TODO: the rv_method/rv_grav are being copied for orbits and stars... but we need kind to apply to rv? (see also for legacy backend)
    # params += [ChoiceParameter(qualifier='rv_method', copy_for = {'kind': 'rv', 'component': '*', 'dataset': '*'}, component='_default', dataset='_default', value=kwargs.get('rv_method', 'flux-weighted'), choices=['flux-weighted', 'dynamical'], description='Method to use for computing RVs (must be flux-weighted for Rossiter-McLaughlin effects)')]
    params += [ChoiceParameter(qualifier='rv_method', copy_for={'component': {'kind': 'star'}, 'dataset': {'kind': 'rv'}}, component='_default', dataset='_default', value=kwargs.get('rv_method', 'flux-weighted'), choices=['flux-weighted', 'dynamical'], description='Method to use for computing RVs (must be flux-weighted for Rossiter-McLaughlin effects)')]
    params += [BoolParameter(visible_if='rv_method:flux-weighted', qualifier='rv_grav', copy_for={'component': {'kind': 'star'}, 'dataset': {'kind': 'rv'}}, component='_default', dataset='_default', value=kwargs.get('rv_grav', False), description='Whether gravitational redshift effects are enabled for RVs')]

    if conf.devel:
        params += [ChoiceParameter(qualifier='etv_method', copy_for = {'kind': ['etv'], 'component': '*', 'dataset': '*'}, component='_default', dataset='_default', value=kwargs.get('etv_method', 'crossing'), choices=['crossing'], description='Method to use for computing ETVs')]
        params += [FloatParameter(visible_if='etv_method:crossing', qualifier='etv_tol', copy_for = {'kind': ['etv'], 'component': '*', 'dataset': '*'}, component='_default', dataset='_default', value=kwargs.get('etv_tol', 1e-4), default_unit=u.d, description='Precision with which to determine eclipse timings')]
    # -----------------------------------------------------------



    return ParameterSet(params)


def legacy(**kwargs):
    """
    Create a <phoebe.parameters.ParameterSet> for compute options for the
    [PHOEBE 1.0 (legacy)](http://phoebe-project.org/1.0) backend.

    See also:
    * <phoebe.frontend.bundle.Bundle.export_legacy>
    * <phoebe.frontend.bundle.Bundle.from_legacy>

    Use PHOEBE 1.0 (legacy) which is based on the Wilson-Devinney code
    to compute radial velocities and light curves for binary systems
    (>2 stars not supported).  The code is available here:

    http://phoebe-project.org/1.0

    PHOEBE 1.0 and the 'phoebeBackend' python interface must be installed
    and available on the system in order to use this plugin.

    When using this backend, please cite
    * Prsa & Zwitter (2005), ApJ, 628, 426

    See also:
    * <phoebe.frontend.bundle.Bundle.references>

    Generally, this will be used as an input to the kind argument in
    <phoebe.frontend.bundle.Bundle.add_compute>.  If attaching through
    <phoebe.frontend.bundle.Bundle.add_compute>, all `**kwargs` will be
    passed on to set the values as described in the arguments below.  Alternatively,
    see <phoebe.parameters.ParameterSet.set_value> to set/change the values
    after creating the Parameters.

    For example:

    ```py
    b.add_compute('legacy')
    b.run_compute(kind='legacy')
    ```

    Arguments
    ----------
    * `enabled` (bool, optional): whether to create synthetics in compute/fitting
        run.
    * `atm` (string, optional): atmosphere tables.
    * `gridsize` (float, optional): number of meshpoints for WD.
    * `irrad_method` (string, optional): which method to use to handle irradiation.
    * `ie` (bool, optional): whether data should be de-reddened.
    * `rv_method` (string, optional): which method to use for computing radial
        velocities.

    Returns
    --------
    * (<phoebe.parameters.ParameterSet>): ParameterSet of all newly created
        <phoebe.parameters.Parameter> objects.
    """
    params = []

    params += [BoolParameter(qualifier='enabled', copy_for={'context': 'dataset', 'kind': ['lc', 'rv', 'mesh'], 'dataset': '*'}, dataset='_default', value=kwargs.get('enabled', True), description='Whether to create synthetics in compute/fitting run')]

    # TODO: the kwargs need to match the qualifier names!
    # TODO: include MORE meshing options
    params += [ChoiceParameter(copy_for = {'kind': ['star'], 'component': '*'}, component='_default', qualifier='atm', value=kwargs.get('atm', 'extern_atmx'), choices=['extern_atmx', 'extern_planckint'], description='Atmosphere table')]
#    params += [ChoiceParameter(copy_for = {'kind': ['star'], 'component': '*'}, component='_default', qualifier='atm', value=kwargs.get('atm', 'kurucz'), choices=['kurucz', 'blackbody'], description='Atmosphere table')]
#    params += [ChoiceParameter(qualifier='morphology', value=kwargs.get('morphology','Detached binary'), choices=['Unconstrained binary system', 'Detached binary', 'Overcontact binary of the W UMa type', 'Overcontact binary not in thermal contact'], description='System type constraint')]
#    params += [BoolParameter(qualifier='cindex', value=kwargs.get('cindex', False), description='Color index constraint')]
#    params += [IntParameter(visible_if='cindex_switch:True', qualifier='cindex', value=kwargs.get('cindex', np.array([1.0])), description='Number of reflections')]
#    params += [BoolParameter(qualifier='heating', value=kwargs.get('heating', True), description='Allow irradiators to heat other components')]
    params += [IntParameter(copy_for={'kind': ['star'], 'component': '*'}, component='_default', qualifier='gridsize', value=kwargs.get('gridsize', 60), limits=(10,None), description='Number of meshpoints for WD')]

    params += [ChoiceParameter(qualifier='irrad_method', value=kwargs.get('irrad_method', 'wilson'), choices=['none', 'wilson'], description='Which method to use to handle irradiation/reflection effects')]
    params += [IntParameter(visible_if='irrad_method:wilson', qualifier='refl_num', value=kwargs.get('refl_num', 1), limits=(0,None), description='Number of reflections')]

#    params += [BoolParameter(qualifier='msc1', value=kwargs.get('msc1', False), description='Mainsequence Constraint for star 1')]
#    params += [BoolParameter(qualifier='msc2', value=kwargs.get('msc2', False), description='Mainsequence Constraint for star 2')]


    # TODO: can we come up with a better qualifier for reddening (and be consistent when we enable in phoebe2)
    params += [BoolParameter(qualifier='ie', value=kwargs.get('ie', False), description='Should data be de-reddened')]

    params += [ChoiceParameter(qualifier='rv_method', copy_for={'component': {'kind': 'star'}, 'dataset': {'kind': 'rv'}}, component='_default', dataset='_default',
                               value=kwargs.get('rv_method', 'flux-weighted'), choices=['flux-weighted', 'dynamical'], description='Method to use for computing RVs (must be flux-weighted for Rossiter-McLaughlin)')]

    return ParameterSet(params)

def photodynam(**kwargs):
    """
    **This backend is EXPERIMENTAL and requires developer mode to be enabled**

    **DO NOT USE FOR SCIENCE**

    Create a <phoebe.parameters.ParameterSet> for compute options for Josh
    Carter's [photodynam](http://github.com/phoebe-project/photodynam) code.

    Use photodynam to compute radial velocities and light curves.
    photodynam must be installed and available on the system in order to use
    this plugin.  The code is available here:

    http://github.com/phoebe-project/photodynam

    When using this backend, please cite
    * Science 4 February 2011: Vol. 331 no. 6017 pp. 562-565 DOI:10.1126/science.1201274
    * MNRAS (2012) 420 (2): 1630-1635. doi: 10.1111/j.1365-2966.2011.20151.x

    See also:
    * <phoebe.frontend.bundle.Bundle.references>

    The following parameters are "exported/translated" when using the photodynam
    backend:

    System:
    * t0

    Star:
    * mass
    * requiv

    Orbit:
    * sma
    * ecc
    * incl
    * per0
    * long_an
    * mean_anom

    Dataset:
    * ld_func (only supports quadratic)
    * ld_coeffs (will use <phoebe.frontend.bundle.Bundle.compute_ld_coeffs> if necessary)
    * pblum (will use <phoebe.frontend.bundle.Bundle.compute_pblums> if necessary)


    The following parameters are populated in the resulting model when using the
    photodynam backend:

    LCs:
    * times
    * fluxes

    RVs (dynamical only):
    * times
    * rvs

    ORBs:
    * times
    * us
    * vs
    * ws
    * vus
    * vvs
    * vws

    Generally, this will be used as an input to the kind argument in
    <phoebe.frontend.bundle.Bundle.add_compute>.  If attaching through
    <phoebe.frontend.bundle.Bundle.add_compute>, all `**kwargs` will be
    passed on to set the values as described in the arguments below.  Alternatively,
    see <phoebe.parameters.ParameterSet.set_value> to set/change the values
    after creating the Parameters.

    For example:

    ```py
    b.add_compute('photodynam')
    b.run_compute(kind='photodynam')
    ```

    Arguments
    ----------
    * `enabled` (bool, optional): whether to create synthetics in compute/fitting
        run.
    * `stepsize` (float, optional, default=0.01): stepsize to use for dynamics
        integration.
    * `orbiterror` (float, optional, default=1e-20): error to use for dynamics
        integration.

    Returns
    --------
    * (<phoebe.parameters.ParameterSet>): ParameterSet of all newly created
        <phoebe.parameters.Parameter> objects.
    """
    if not conf.devel:
        raise NotImplementedError("'photodynam' backend not officially supported for this release.  Enable developer mode to test.")

    params = []

    params += [BoolParameter(qualifier='enabled', copy_for={'context': 'dataset', 'kind': ['lc', 'rv', 'orb'], 'dataset': '*'}, dataset='_default', value=kwargs.get('enabled', True), description='Whether to create synthetics in compute/fitting run')]

    params += [FloatParameter(qualifier='stepsize', value=kwargs.get('stepsize', 0.01), default_unit=None, description='Stepsize to use for dynamics integration')]
    params += [FloatParameter(qualifier='orbiterror', value=kwargs.get('orbiterror', 1e-20), default_unit=None, description='Error to use for dynamics integraton')]

    # TODO: remove this option and instead use time0@system
    #params += [FloatParameter(qualifier='time0', value=kwargs.get('time0', 0.0), default_unit=u.d, description='Time to start the integration')]

    return ParameterSet(params)

def jktebop(**kwargs):
    """
    **This backend is EXPERIMENTAL and requires developer mode to be enabled**

    **DO NOT USE FOR SCIENCE**

    Create a <phoebe.parameters.ParameterSet> for compute options for John
    Southworth's [jktebop](http://www.astro.keele.ac.uk/jkt/codes/jktebop.html) code.

    Use jktebop to compute radial velocities and light curves for binary systems.
    jktebop must be installed and available on the system in order to use
    this plugin.  The code is available here (currently tested with v34):

    http://www.astro.keele.ac.uk/jkt/codes/jktebop.html

    Please see the link above for a list of publications to cite when using this
    code.

    See also:
    * <phoebe.frontend.bundle.Bundle.references>

    According to jktebop's website: "jktebop models the two components as
    biaxial spheroids for the calculation of the reflection and ellipsoidal
    effects, and as spheres for the eclipse shapes."

    Note that the wrapper around jktebop only uses its forward model.
    jktebop also includes its own fitting methods, including bootstrapping.
    Those capabilities cannot be accessed from PHOEBE.

    The following parameters are "exported/translated" when using the jktebop
    backend:

    Star:
    * requiv
    * gravb_bol
    * irrad_frac_refl_bol
    * teff (currently used as an estimate for surface brightness ratio)

    Orbit:
    * sma
    * incl
    * q
    * ecos
    * esinw
    * period
    * t0_supconj

    Dataset (LC only):
    * ld_func (must not be 'interp')
    * ld_coeffs (will call <phoebe.frontend.bundle.Bundle.compute_ld_coeffs> if necessary)
    * pblum (will use <phoebe.frontend.bundle.Bundle.compute_pblums> if necessary)


    The following parameters are populated in the resulting model when using the
    jktebop backend:

    LCs:
    * times
    * fluxes

    Generally, this will be used as an input to the kind argument in
    <phoebe.frontend.bundle.Bundle.add_compute>.  If attaching through
    <phoebe.frontend.bundle.Bundle.add_compute>, all `**kwargs` will be
    passed on to set the values as described in the arguments below.  Alternatively,
    see <phoebe.parameters.ParameterSet.set_value> to set/change the values
    after creating the Parameters.

    For example:

    ```py
    b.add_compute('jktebop')
    b.run_compute(kind='jktebop')
    ```

    Arguments
    ----------
    * `enabled` (bool, optional): whether to create synthetics in compute/fitting
        run.
    * `ringsize` (float, optional, default=5): integration ring size.

    Returns
    --------
    * (<phoebe.parameters.ParameterSet>): ParameterSet of all newly created
        <phoebe.parameters.Parameter> objects.
    """
    if not conf.devel:
        raise NotImplementedError("'jktebop' backend not officially supported for this release.  Enable developer mode to test.")

    params = []

    params += [BoolParameter(qualifier='enabled', copy_for={'context': 'dataset', 'kind': ['lc'], 'dataset': '*'}, dataset='_default', value=kwargs.get('enabled', True), description='Whether to create synthetics in compute/fitting run')]

    params += [FloatParameter(qualifier='ringsize', value=kwargs.get('ringsize', 5), default_unit=u.deg, description='Integ Ring Size')]

    return ParameterSet(params)

def ellc(**kwargs):
    """
    **This backend is EXPERIMENTAL and requires developer mode to be enabled**

    **DO NOT USE FOR SCIENCE**

    Create a <phoebe.parameters.ParameterSet> for compute options for Pierre
    Maxted's [ellc](https://github.com/pmaxted/ellc) code.

    Use ellc to compute radial velocities and light curves for binary systems.
    ellc must be installed and available on the system in order to use
    this plugin (tested with v 1.8.1).  The code is available here:

    https://github.com/pmaxted/ellc

    and can be installed via pip:

    ```py
    pip install ellc
    ```

    Please cite the following when using this backend:

    https://ui.adsabs.harvard.edu/abs/2016A%26A...591A.111M/abstract

    See also:
    * <phoebe.frontend.bundle.Bundle.references>

    Note that the wrapper around ellc only uses its forward model.
    ellc also includes its own fitting methods, including emccee.
    Those capabilities cannot be accessed from PHOEBE.

    The following parameters are "exported/translated" when using the ellc
    backend:

    Star:
    * requiv
    * syncpar
    * gravb_bol

    Orbit:
    * sma
    * period
    * q
    * incl
    * ecc
    * per0
    * dperdt
    * t0_supconj

    Dataset (LC/RV only):
    * l3
    * ld_func (must not be 'interp')
    * ld_coeffs (will call <phoebe.frontend.bundle.Bundle.compute_ld_coeffs> if necessary)
    * pblum (will use <phoebe.frontend.bundle.Bundle.compute_pblums> if necessary)

    Note: ellc returns fluxes in arbitrary units.  These are then rescaled according
    to the values of pblum, but converted to a flux-scale by assuming spherical stars.
    For the non-spherical case, the fluxes may be off by a (small) factor.


    The following parameters are populated in the resulting model when using the
    ellc backend:

    LCs:
    * times
    * fluxes

    RVs:
    * times
    * rvs

    Generally, this will be used as an input to the kind argument in
    <phoebe.frontend.bundle.Bundle.add_compute>.  If attaching through
    <phoebe.frontend.bundle.Bundle.add_compute>, all `**kwargs` will be
    passed on to set the values as described in the arguments below.  Alternatively,
    see <phoebe.parameters.ParameterSet.set_value> to set/change the values
    after creating the Parameters.

    For example:

    ```py
    b.add_compute('ellc')
    b.run_compute(kind='ellc')
    ```

    Arguments
    ----------
    * `enabled` (bool, optional): whether to create synthetics in compute/fitting
        run.
    * `distortion_method` (string, optional, default='roche'): method to use
        for distorting stars.
    * `hf` (float, optional, default=1.5): fluid second love number (only applicable
        if/when `distortion_method`='love')
    * `grid` (string, optional, default='default'): grid size used to calculate the flux.
    * `exact_grav` (bool, optional, default=False): whether to use point-by-point
        calculation of local surface gravity for calculation of gravity darkening
        or a (much faster) approximation based on functional form fit to local
        gravity at 4 points on the star.
    * `rv_method` (string, optional, default='flux-weighted'): which method to
        use for computing radial velocities.
    * `fti_method` (string, optional, default='none'): method to use when accounting
        for finite exposure times.
    * `fti_oversample` (int, optional, default=1): number of integration points
        used to account for finite exposure time.  Only used if `fti_method`='oversample'.


    Returns
    --------
    * (<phoebe.parameters.ParameterSet>): ParameterSet of all newly created
        <phoebe.parameters.Parameter> objects.
    """
    if not conf.devel:
        raise NotImplementedError("'ellc' backend not officially supported for this release.  Enable developer mode to test.")

    params = []

    params += [BoolParameter(qualifier='enabled', copy_for={'context': 'dataset', 'kind': ['lc', 'rv'], 'dataset': '*'}, dataset='_default', value=kwargs.get('enabled', True), description='Whether to create synthetics in compute/fitting run')]

    params += [ChoiceParameter(copy_for={'kind': ['star'], 'component': '*'}, component='_default', qualifier='distortion_method', value=kwargs.get('distortion_method', 'roche'), choices=["roche", "roche_v", "sphere", "poly1p5", "poly3p0", "love"], description='Method to use for distorting stars')]
    params += [FloatParameter(visible_if='distortion_method:love', copy_for={'kind': ['star'], 'component': '*'}, component='_default', qualifier='hf', value=kwargs.get('hf', 1.5), limits=(0,None), default_unit=u.dimensionless_unscaled, description='fluid second love number for radial displacement')]


    params += [ChoiceParameter(copy_for={'kind': ['star'], 'component': '*'}, component='_default', qualifier='grid', value=kwargs.get('grid', 'default'), choices=['very_sparse', 'sparse', 'default', 'fine', 'very_fine'], description='Grid size used to calculate the flux.')]

    params += [BoolParameter(qualifier='exact_grav', value=kwargs.get('exact_grav', False), description='Whether to use point-by-point calculation of local surface gravity for calculation of gravity darkening or a (much faster) approximation based on functional form fit to local gravity at 4 points on the star.')]

    params += [ChoiceParameter(qualifier='rv_method', copy_for = {'kind': ['rv'], 'component': '*', 'dataset': '*'}, component='_default', dataset='_default',
                               value=kwargs.get('rv_method', 'flux-weighted'), choices=['flux-weighted', 'dynamical'], description='Method to use for computing RVs (must be flux-weighted for Rossiter-McLaughlin)')]


    # copy for RV datasets once exptime support for RVs in phoebe
    params += [ChoiceParameter(qualifier='fti_method', copy_for = {'kind': ['lc'], 'dataset': '*'}, dataset='_default', value=kwargs.get('fti_method', 'none'), choices=['none', 'oversample'], description='How to handle finite-time integration (when non-zero exptime)')]
    params += [IntParameter(visible_if='fit_method:oversample', qualifier='fti_oversample', copy_for={'kind': ['lc'], 'dataset': '*'}, dataset='_default', value=kwargs.get('fti_oversample', 5), limits=(1, None), default_unit=u.dimensionless_unscaled, description='number of integration points used to account for finite exposure time.')]


    return ParameterSet(params)
