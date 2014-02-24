
"""
What kind of stuff do we need in a data model?

General
 * users (at a minimum user_id and external ID for SSO.)

Batch
 *


For fermentation

 * a fermentation - usually a beer, comprises
 ** various temperature series, PV/SV for beer temp, beer actuator states
 ** name
 ** owner
 * relations to other series:
 ** chamber control


 Chamber control - the chamber control may span several brews in the data an exists outside of any particular brew
  * PV/SV for chamber, chamber actuator states, controller states
  * ambient temp


For mashing
 * a mash
 ** various time series: data points for PV/SV mash temp, hlt temp, ambient temp, actuator states, controller states, custom annotations
 ** profile (defines as interpolated time point profile for temperature.)
 * related to brew batch (so brew can be tracked through all parts of the brew-cycle)


For stirplate
 * name
 * beer batch?
 * yeast strain, bbe date
 * type (see Mr Malty calculator)
 * predicted cell count etc..
 * temperature profile
 * time series


Generally for a tracked brewing process
* name
* type (subclass)
* batch
* various time series
** each time series should know it's source of data (both physical e.g. onewire address/arduino ID and logical - controller ID and logical sensor?)
* associated monitors (adding/removing monitors is also tracked as events.)
*

Examples of monitors:
- after activating a heater, the temperature should rise
- after activating a cooler, the temperature should rall
- general alarm conditions for temperature out of bounds (e.g. after stabilizing, beer temp should be 0.5C of set point)
-

Rethink profile:
- it's basically a system controlled PV
- could be temperature, but equally an activator state (on/off or %)
- could be rate of SG change, although I'm not sure constant is ideal, since the process is much more complex.
- could be any other kind of process variable that we can indirectly control

"""



__author__ = 'mat'
