from __future__ import annotations 
from dataclasses import dataclass, field, InitVar
import numpy as np
from py_vol_surface import utils
from typing import Any
import copy
from py_vol_surface import misc_widgets
from typing import Dict, ClassVar, Optional
from py_vol_surface import exceptions
import warnings
from pydantic.dataclasses import dataclass as pdataclass

def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    print(f"UserWarning: {message} ({filename}, line {lineno})")
warnings.showwarning = custom_showwarning


@dataclass(slots=True)
class Raw:
    n_options: np.ndarray = field(init=False, default_factory=np.array)
    ivol: np.ndarray = field(init=False, default_factory=np.array)
    delta: np.ndarray = field(init=False, default_factory=np.array)
    delta_mag: np.ndarray = field(init=False, default_factory=np.array)
    gamma: np.ndarray = field(init=False, default_factory=np.array)
    vega: np.ndarray = field(init=False, default_factory=np.array)
    moneyness: np.ndarray = field(init=False, default_factory=np.array)
    log_moneyness: np.ndarray = field(init=False, default_factory=np.array)
    standardised_moneyness: np.ndarray = field(init=False, default_factory=np.array)
    OTM: np.ndarray = field(init=False, default_factory=np.array)
    call_flag: np.ndarray = field(init=False, default_factory=np.array)
    valid_price: np.ndarray = field(init=False, default_factory=np.array)
    underlying_price: np.ndarray = field(init=False, default_factory=np.array)
    
    def __init__(self, n_options):
        self.n_options = n_options
        self.ivol = np.full(n_options, np.nan)
        self.delta = np.full(n_options, np.nan)
        self.delta_mag = np.full(n_options, np.nan)
        self.gamma = np.full(n_options, np.nan)
        self.vega = np.full(n_options, np.nan)
        self.moneyness = np.full(n_options, np.nan)
        self.log_moneyness = np.full(n_options, np.nan)
        self.standardised_moneyness = np.full(n_options, np.nan)
        self.OTM = np.array([True] * n_options)
        self.call_flag = np.array([True] * n_options)
        self.valid_price= np.array([False] * n_options)
        self.underlying_price = np.full(n_options, np.nan)

    def update_IVOL(self, idx, implied_volatility):
        self.ivol[idx] = implied_volatility
    
    def update_all_metrics(self, idx, jdx, ivol, delta, delta_mag, gamma, vega, moneyness,
                           log_moneyness, standardised_moneyness, OTM, call_flag, valid_price, underlying_price):
        self.ivol[idx] = ivol[jdx]
        self.delta[idx] = delta[jdx]
        self.delta_mag[idx] = delta_mag[jdx]
        self.gamma[idx] = gamma[jdx]
        self.vega[idx] = vega[jdx]
        self.moneyness[idx] = moneyness
        self.log_moneyness[idx] = log_moneyness
        self.standardised_moneyness[idx] = standardised_moneyness[jdx]
        self.OTM[idx] = OTM
        self.call_flag[idx] = call_flag
        self.valid_price[idx]=valid_price
        self.underlying_price[idx]=underlying_price
    
    def update_with_instrument_object(self, idx, option_object, ivol, update_list):
        self.ivol[idx] = ivol
        for metric in update_list:    
            getattr(self, metric)[idx] = getattr(option_object, metric)
       

@dataclass(slots=True, frozen=True)
class BaseDomain:
    strike: np.ndarray
    expiry: np.ndarray
    x_metric: str
    y_metric: str
    
        
@dataclass(slots=True)
class Domain:
    base_domain: BaseDomain
    x: np.ndarray = field(init=False, default_factory=lambda: np.array)
    y: np.ndarray = field(init=False, default_factory=lambda: np.array)
    x_vect: np.ndarray = field(init=False, default_factory=lambda: np.array)
    y_vect: np.ndarray = field(init=False, default_factory=lambda: np.array)
    x_mat: np.ndarray = field(init=False, default_factory=lambda: np.array)
    y_mat: np.ndarray = field(init=False, default_factory=lambda: np.array)
    z_mat: np.ndarray = field(init=False, default_factory=lambda: np.array)

    xy: np.ndarray = field(init=False, default_factory=lambda: np.array)
    idx_ij_mapping: Dict[int, tuple] = field(init=False, default_factory=dict)
    z_mat: float = field(init=False, default_factory=lambda: np.array)
    
    def __post_init__(self):
        self._create_domain(self.base_domain.strike.copy(), self.base_domain.expiry.copy())

    def _create_domain(self, x, y):
        self.x = x
        self.y = y
        self.xy = np.column_stack((self.x, self.y)) 

        self.x_vect = np.unique(self.base_domain.strike)
        self.y_vect = np.unique(self.base_domain.expiry)

        self.x_mat, self.y_mat = np.meshgrid(self.x_vect, self.y_vect, indexing="xy")
        self.z_mat = np.full(self.x_mat.shape, np.nan)
        
        self.idx_ij_mapping = {}
        
        for i in range(self.x_mat.shape[0]):
            for j in range(self.x_mat.shape[1]):
                match_idx = np.where((self.xy == [self.x_mat[i, j], self.y_mat[i, j]]).all(axis=1))[0]
                for idx in match_idx:
                    self.idx_ij_mapping[idx] = (i, j)

    def update_data(self, z, idx_map):
        for idx, ivol in zip(idx_map, z):
            if idx in self.idx_ij_mapping:
                i, j = self.idx_ij_mapping[idx]
                self.z_mat[i,j] = ivol


    def switch_axis(self):
        pass



    def update(self, x=None, y=None, xy=None, z=None, x_metric=None, y_metric=None, z_metric=None):
        if not xy is None:
            self.xy = xy
            self.x = xy[:,0]
            self.y = xy[:,1]
        else:
            self.x = x
            self.y = y
            self.xy = np.column_stack((x,y))
        if not z is None:
            self.z = z
        if x_metric:
            self.x_metric = x_metric
        if y_metric:
            self.y_metric = y_metric
        self._calc_metrics()
    
    
@dataclass(slots=True)
class Scatter:  
    x: np.ndarray 
    y: np.ndarray 
    z: np.ndarray
    colour: tuple
    
    x_min: float = np.nan
    x_max: float = np.nan
    y_min: float = np.nan
    y_max: float = np.nan
    z_min: float = np.nan
    z_max: float = np.nan
    valid_values: bool = False
    
    x_min: float = field(init=False, default = np.nan)
    x_max: float = field(init=False, default = np.nan)
    y_min: float = field(init=False, default = np.nan)
    y_max: float = field(init=False, default = np.nan)
    z_min: float = field(init=False, default = np.nan)
    z_max: float = field(init=False, default = np.nan)
    
    valid_values: bool = field(init=False, default=False)
    
    def __post_init__(self):
        self.update_data(self.x, self.y, self.z)
        
    def get_limits(self,):
        return self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max
    
    def update_data(self, x, y, z):
        self.valid_values=False
        self.x, self.y, self.z = utils.filter_nans_on_z(x, y, z)

        if self.z.size > 0:
            self.valid_values=True
            self._calc_metrics()

    def _calc_metrics(self):
        self.x_min = np.amin(self.x)
        self.x_max = np.amax(self.x)
        self.y_min = np.amin(self.y)
        self.y_max = np.amax(self.y)
        self.z_min = np.amin(self.z)
        self.z_max = np.amax(self.z)
                
        
@dataclass(slots=True)
class Surface:
    scatter: Scatter
    interpolator: Any
    n_x: int
    n_y: int
    colourmap_style:str

    x: np.ndarray = field(init=False, default_factory=lambda: np.array)
    y: np.ndarray = field(init=False, default_factory=lambda: np.array)
    z: np.ndarray = field(init=False, default_factory=lambda: np.array)
            
    x_min: float = field(init=False, default=np.nan)
    x_max: float = field(init=False, default=np.nan)
    y_min: float = field(init=False, default=np.nan)
    y_max: float = field(init=False, default=np.nan)
    
    z_min: float = field(init=False, default=np.nan)
    z_max: float = field(init=False, default=np.nan)
    
    valid_values: bool = field(init=False, default=False)
    last_interpolation_attempt_valid: bool = field(init=False, default=False)
    current_view_selection: str = field(init=False, default="Surface")
    
    colourmap: 'misc_widgets.CustomColorMap' = field(init=False, default=None)
    
    def __post_init__(self):   
        self.colourmap = misc_widgets.CustomColorMap(self.colourmap_style)
        self.x=self.scatter.x
        self.y=self.scatter.y
        self._create_interpolation_limits(self.scatter)
        if self.scatter.valid_values:
            self.interpolate_surface()
        else:
            self.z = np.nan * np.zeros((self.n_x, self.n_y))
        
    def get_limits(self,):
        return self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max

    def update_table(self, scatter_object):
        self.create_tradeable_domain(scatter_object)
        
        for (x, y, z_val) in zip(scatter_object.x, scatter_object.y, scatter_object.z):
            i = np.where(self.x == x)[0][0]
            j = np.where(self.y == y)[0][0]
            self.z[i, j] = z_val
    
    def update_data_from_scatter_object(self, scatter_object):
        if (self.x_min != scatter_object.x_min
            or self.x_max != scatter_object.x_max
            or self.y_min != scatter_object.y_min
            or self.y_max != scatter_object.y_max):

            self.x_min = scatter_object.x_min 
            self.x_max = scatter_object.x_max
            self.y_min = scatter_object.y_min
            self.y_max = scatter_object.y_max

            self.x = np.linspace(self.x_min, self.x_max, self.n_x)
            self.y = np.linspace(self.y_min, self.y_max, self.n_y)

    def _create_interpolation_limits(self, scatter_object, extension_x=[0,0], extension_y=[0,0]):
        self.x_min = scatter_object.x_min + extension_x[0]
        self.x_max = scatter_object.x_max + extension_x[1]
        self.y_min = scatter_object.y_min + extension_y[0]
        self.y_max = scatter_object.y_max + extension_y[1]

        self.x = np.linspace(self.x_min, self.x_max, self.n_x)
        self.y = np.linspace(self.y_min, self.y_max, self.n_y)

    def interpolate_surface(self):
        self.valid_values=False
        x, y, z = utils.filter_nans_on_z(self.scatter.x, self.scatter.y, self.scatter.z)
        if z.size < 5:
            warnings.warn(exceptions.InsufficientDataWarning(
                        f"Unable to interpolate: z has only {z.size} points (min 5 required)", 
                code=100
            ),
            stacklevel=2  # Point to the caller's line
        )
            self.last_interpolation_attempt_valid = False
            return
        try:
            self.interpolator.fit(x, y, z)                
        except Exception as e:
            print(f"The interpolator could not fit: {e}")
            self.last_interpolation_attempt_valid=False
            return
        try:
            self.z = self.interpolator.evaluate(self.x, self.y)
        except Exception as e:
            print(f"The interpolator could not evaluate: {e}")
            self.last_interpolation_attempt_valid=False
            return
        
        if not self.last_interpolation_attempt_valid:
            print("The last interpolation was valid")
        self.last_interpolation_attempt_valid=True
        
        self.z_min = np.nanmin(self.z)
        self.z_max = np.nanmax(self.z)
        self.valid_values=True


@dataclass
class Smirk:
    domain: Domain
    raw: Raw
    interpolator: Any
    
    xy: np.ndarray = field(init=False, default_factory=np.array)
    
    def __post_init__(self):
        self.xy = self.domain.xy
                


@dataclass
class DataContainer:
    price_type: Optional[str] = None
    raw: Optional["Raw"] = None
    scatter: Optional["Scatter"] = None
    surface: Optional["Surface"] = None
    domain: Optional["Domain"] = None
    base_domain: ClassVar[BaseDomain]
    
    def __post_init__(self):
        if not self.scatter is None and not self.surface is None:
            self._calculate_data_limits()
    
    def update_dataclasses(self, x, y, z, idx_map):
        self.scatter.update_data(x, y, z)
        self.surface.update_data_from_scatter_object(self.scatter)
        self.domain.update_data(z, idx_map)
        self.surface.interpolate_surface()
        self._calculate_data_limits()
    
    def _calculate_data_limits(self):
        self.x_min = np.minimum(self.scatter.x_min, self.surface.x_min)
        self.x_max = np.maximum(self.scatter.x_max, self.surface.x_max) 
        self.y_min = np.minimum(self.scatter.y_min, self.surface.y_min)
        self.y_max = np.maximum(self.scatter.y_max, self.surface.y_max) 
        
        if self.scatter.valid_values and self.surface.valid_values:
            self.z_min = np.minimum(self.scatter.z_min, self.surface.z_min)
            self.z_max = np.maximum(self.scatter.z_max, self.surface.z_max) 
        elif self.scatter.valid_values:
            self.z_min = self.scatter.z_min
            self.z_max = self.scatter.z_max
        elif self.surface.valid_values:
            self.z_min=self.surface.z_min
            self.z_max=self.surface.z_max
        
    def create_from_scratch(self, n_options, price_type, instrument_manager, axis_transformer, interpolation_config, colour_config):
        self.price_type = price_type
        self.raw = Raw(n_options)
        for option_name, option_object in instrument_manager.options.items():
            idx = instrument_manager.options_maps.name_index_map[option_name]
            jdx = option_object.price_type_idx_map[price_type]
            self.raw.update_all_metrics(idx, jdx, *option_object.get_all_metrics(), option_object.valid_price) 
        
        x, y, z, idx_map = axis_transformer.transform_data(self.raw)
        
        self.scatter = Scatter(x, y, z, colour_config["scatter"][self.price_type])
        self.surface = Surface(self.scatter,
                               copy.deepcopy(interpolation_config["engine"]),
                               interpolation_config["n_x"],
                               interpolation_config["n_y"],
                               colour_config["surface"][self.price_type])
        self.domain = Domain(self.base_domain)
        
        self._calculate_data_limits()
        return self        


@dataclass
class DataFeatureManager:
    price_types: list

    limit_dict: dict = field(init=False)
    valid_values_dict: dict = field(init=False)
    valid_values_any: bool = False
    
    all_axis: ClassVar[list] = ["x","y","z"]
    plot_types: ClassVar[list] = ["scatter", "surface"]
    _reset_dict: ClassVar[dict] = {"min" : np.nan, "max" : np.nan}
    
    def __post_init__(self):
        self.limit_dict = {}
        self.valid_values_dict = {}
        for price_type in self.price_types:
            plot_dict_lim = {}
            plot_dict_bool = {}
            for plot_type in self.plot_types:
                axis_dict_lim = {}
                for axis in self.all_axis:
                    axis_dict_lim[axis] = copy.deepcopy(self._reset_dict)
                plot_dict_lim[plot_type] = axis_dict_lim
                plot_dict_bool[plot_type] = False
                
            self.limit_dict[price_type] = plot_dict_lim
            self.valid_values_dict[price_type] = plot_dict_bool

    def remove_data(self, price_type):
        for axis in self.all_axis:
            self.limit_dict[price_type]["surface"][axis] = copy.deepcopy(self._reset_dict)
            self.limit_dict[price_type]["scatter"][axis] = copy.deepcopy(self._reset_dict)
            
        self.valid_values_dict[price_type]["surface"]=False
        self.valid_values_dict[price_type]["scatter"]=False

    def find_any_valid_values(self, data_container_manager_object: DataContainerManager.object):
        bool_arr = []
        z_vals = []
        for price_type, data_container in data_container_manager_object.items():
            if data_container.surface.valid_values:
                for axis in self.all_axis:
                    axis_min = getattr(data_container.surface, f"{axis}_min")
                    axis_max = getattr(data_container.surface, f"{axis}_max")
                    self.limit_dict[price_type]["surface"][axis]["min"] = axis_min
                    self.limit_dict[price_type]["surface"][axis]["max"] = axis_max
                    bool_arr.append(True)
                    self.valid_values_dict[price_type]["surface"] = True
                z_vals.append(self.limit_dict[price_type]["surface"]["z"]["min"])
                z_vals.append(self.limit_dict[price_type]["surface"]["z"]["max"])
            else:
                for axis in self.all_axis:
                    self.limit_dict[price_type]["surface"][axis]["min"] = np.nan
                    self.limit_dict[price_type]["surface"][axis]["max"] = np.nan
                    self.valid_values_dict[price_type]["surface"] = False

            if data_container.scatter.valid_values:
                for axis in self.all_axis:
                    axis_min = getattr(data_container.scatter, f"{axis}_min")
                    axis_max = getattr(data_container.scatter, f"{axis}_max")
                    self.limit_dict[price_type]["scatter"][axis]["min"] = axis_min
                    self.limit_dict[price_type]["scatter"][axis]["max"] = axis_max
                    bool_arr.append(True)
                    self.valid_values_dict[price_type]["scatter"] = True
                z_vals.append(self.limit_dict[price_type]["scatter"]["z"]["min"])
                z_vals.append(self.limit_dict[price_type]["scatter"]["z"]["max"])
            else:
                self.limit_dict[price_type]["scatter"][axis]["min"] = np.nan
                self.limit_dict[price_type]["scatter"][axis]["max"] = np.nan
                self.valid_values_dict[price_type]["scatter"] = False
        
        self.valid_values_any = any(bool_arr)
        if self.valid_values_any:
            return True, z_vals
        else:
            return False, z_vals
          
                                                      
@dataclass
class DataContainerManager:
    price_types: InitVar[list]
    data_container: InitVar[DataContainer] = None
    
    objects: dict = field(init=False, default_factory=dict)
    x_min: float = field(init=False, default=np.nan)
    x_max: float = field(init=False, default=np.nan)
    y_min: float = field(init=False, default=np.nan)
    y_max: float = field(init=False, default=np.nan)
    z_min: float = field(init=False, default=np.nan)
    z_max: float = field(init=False, default=np.nan)

    features: DataFeatureManager = None

    def __post_init__(self, price_types, data_container: DataContainer):
        self.features = DataFeatureManager(price_types)
        
        if not data_container is None:
            self.add_container(data_container)
            
    def add_container(self, data_container):
        self.objects[data_container.price_type] = data_container
        self.calculate_data_limits()
    
    def remove_container(self, price_type):
        del self.objects[price_type]
        self.features.remove_data(price_type)
        self.calculate_data_limits()

    def process_update(self):
        if len(self.objects) > 0:
            self.calculate_data_limits()
        
    def calculate_data_limits(self):
        if len(self.objects) > 0:
            self.x_min = np.min([data_container.x_min for data_container in self.objects.values()])
            self.x_max = np.max([data_container.x_max for data_container in self.objects.values()])
            self.y_min = np.min([data_container.y_min for data_container in self.objects.values()])
            self.y_max = np.max([data_container.y_max for data_container in self.objects.values()])
            valid_values_any, z_vals = self.features.find_any_valid_values(self.objects)
            if valid_values_any:
                self.z_min, self.z_max = np.amin(z_vals), np.amax(z_vals)
            else:
                self.z_min, self.z_max = np.nan, np.nan
        else:
            self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max = [np.nan] * 6
            self.valid_values_any=False
            
    def get_limits(self):
        return self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max
    
    def generate_mask_from_domain_lims(self, x, y):
        return (self.x_min < x) & (x < self.x_max) & (self.y_min < y) & (y < self.y_max)

def create_init_dataclasses(df_options, price_types):
    base_domain = BaseDomain(df_options["strike"].values,
                             df_options["expiry"].values,
                             "Expiry",
                             "Strike")
    
    DataContainer.base_domain=base_domain
    data_container_manager = DataContainerManager(price_types)
    return data_container_manager, base_domain


