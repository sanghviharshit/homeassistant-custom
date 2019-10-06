"""
Mint accounts sensor.

For more details about this platform, please refer to the documentation at
https://github.com/custom-components/sensor.mint
"""

import logging
import voluptuous as vol
import json
import time
from datetime import timedelta
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (PLATFORM_SCHEMA)
from homeassistant.util import Throttle

from homeassistant.const import (
    ATTR_ATTRIBUTION, CONF_ID, CONF_NAME, CONF_USERNAME, CONF_PASSWORD)

__version__ = '0.1.0'

CONF_ATTRIBUTION = "Intuit Mint"
CONF_EXCLUDE_ACCOUNTS = 'exclude_accounts'

CONF_UNIT_OF_MEASUREMENT = 'unit_of_measurement'
CONF_CATEGORIES = 'monitored_categories'
CONF_ACCOUNT_CURRENCY_OVERRIDE = 'account_currency_override'

SESSION_PATH = '.mint-session'
# DATA_MINT = 'mint_cache'

ATTR_NETWORTH = 'networth'
ATTR_ASSETS = 'assets'
ATTR_LIABILITIES = 'liabilities'

# Mint account types
ATTR_INVESTMENT = 'investment'
ATTR_MORTGAGE = 'mortgage'
ATTR_CASH = 'bank'
ATTR_OTHER_ASSET = 'other property'
ATTR_CREDIT = 'credit'
ATTR_LOAN = 'loan'
ATTR_REAL_ESTATE = 'real estate'
ATTR_VEHICLE = 'vehicle'
ATTR_UNCLASSIFIED = 'unclassified'

SCAN_INTERVAL = timedelta(minutes=1)
MIN_TIME_BETWEEN_UPDATES = 5 * 60 # 5 minutes
HEADLESS = False

SENSOR_TYPES = {
    ATTR_INVESTMENT: ['INVESTMENT', 'Investment', False],
    ATTR_MORTGAGE: ['MORTGAGE', 'Mortgage', True],
    ATTR_CASH: ['BANK', 'Cash', False],
    ATTR_OTHER_ASSET: ['OTHER_ASSETS', 'Other Asset', False],
    ATTR_CREDIT: ['CREDIT_CARD', 'Credit', True],
    ATTR_LOAN: ['LOAN', 'Loan', True],
    ATTR_VEHICLE: ['VEHICLE', 'Vehicle', False],
    ATTR_REAL_ESTATE: ['REAL_ESTATE', 'Real Estate', False],
}

ASSET_ACCOUNT_TYPES = [ATTR_INVESTMENT, ATTR_CASH, ATTR_OTHER_ASSET, ATTR_VEHICLE, ATTR_REAL_ESTATE]
LIABILITY_ACCOUNT_TYPES = [ATTR_MORTGAGE, ATTR_CREDIT, ATTR_LOAN]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_UNIT_OF_MEASUREMENT, default='USD'): cv.string,
    vol.Optional(CONF_CATEGORIES, default=[]): vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_EXCLUDE_ACCOUNTS):
        vol.All(cv.ensure_list, [cv.positive_int]),
    vol.Optional(CONF_ACCOUNT_CURRENCY_OVERRIDE):
        vol.All(cv.ensure_list, [{
            cv.string :
                vol.All(cv.ensure_list, [cv.positive_int])
            }]),
})

_CONFIGURING = {}
_LOGGER = logging.getLogger(__name__)

mint_client = None

def setup_platform(hass, config, add_devices, discovery_info=None):
    mint_client = MintClient(config)
    uom = config[CONF_UNIT_OF_MEASUREMENT]
    sensors = []
    categories = config[CONF_CATEGORIES] if len(config[CONF_CATEGORIES]) > 0 else SENSOR_TYPES.keys()
    sensors.append(MintNetWorthSensor(mint_client, config))
    for category in categories:
        sensors.append(MintCategorySensor(hass, mint_client, config, category))
    add_devices(sensors, True)


class MintClient(Entity):

    def __init__(self, config):
        self.mint_client = None
        self.config = config
        self.mint_client = self.getMintClient()

    def getMintClient(self, new_session=True):
        from mintapi import Mint
        from mintapi.api import MintException

        username = self.config.get(CONF_USERNAME)
        password = self.config.get(CONF_PASSWORD)

        try:
            # Init Mint client
            if new_session and self.mint_client:
                self.mint_client.close()

            mint_client = Mint(username,
                password,
                session_path=SESSION_PATH,
                # wait_for_sync=False,
                headless=HEADLESS)
            return mint_client
        except  MintException as exp:
            _LOGGER.error('Error occured while getting mint client')

    def get_accounts(self):
        from mintapi import Mint
        from mintapi.api import MintException

        try:
            return self.mint_client.get_accounts()
        except  MintException as exp:
            self.mint_client = self.getMintClient(new_session=True)
            return self.get_accounts()

class MintNetWorthSensor(Entity):
    """Representation of a personalcapital.com net worth sensor."""
    last_used = time.time() - MIN_TIME_BETWEEN_UPDATES

    def __init__(self, mint_client, config):
        """Initialize the sensor."""
        self._mint_client = mint_client
        self._unit_of_measurement = config[CONF_UNIT_OF_MEASUREMENT]
        self._config = config
        self._state = None
        self._assets = None
        self._liabilities = None
        self.update()

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest state of the sensor."""
        _LOGGER.info('Updating mint networth')
        # self._mint_client.initiate_account_refresh()

        # next_update = MintNetWorthSensor.last_used + MIN_TIME_BETWEEN_UPDATES
        # _LOGGER.info('Last used: {}, Time since: {}'.format(MintNetWorthSensor.last_used, time.time() - MintNetWorthSensor.last_used))
        # if self._mint_client and self._mint_client.driver and time.time() < next_update:
        data = self._mint_client.get_accounts()
        # if time.time() > next_update:

        MintNetWorthSensor.last_used = time.time()
        active_accounts = [account for account in data if account['isActive'] == True and account['isAccountNotFound'] == False and account['isClosed'] == False]
        asset_accounts = [account for account in data if account['isActive'] == True and account['isAccountNotFound'] == False and account['isClosed'] == False and account['accountType'] in ASSET_ACCOUNT_TYPES]
        liability_accounts = [account for account in data if account['isActive'] == True and account['isAccountNotFound'] == False and account['isClosed'] == False and account['accountType'] in LIABILITY_ACCOUNT_TYPES]

        account_currency_overrides = self._config.get(CONF_ACCOUNT_CURRENCY_OVERRIDE)

        # Format +/- balance according to it's accountType
        for active_account in active_accounts:
            active_account['currentBalance'] = format_balance(SENSOR_TYPES[active_account['accountType']][2], active_account['currentBalance'])

        if account_currency_overrides:
            from currency_converter import CurrencyConverter
            converter = CurrencyConverter()

            # _LOGGER.info('Account currency overrides: {}'.format(json.dumps(account_currency_overrides)))
            for account_currency in account_currency_overrides:
                for currency in account_currency.keys():
                    override_accounts = account_currency[currency]
                    _LOGGER.info("{}-{}".format(currency, override_accounts))
                    for override_account in override_accounts:
                        for active_account in active_accounts:
                            if active_account['id'] == override_account:
                                converted_balance = round(converter.convert(active_account['currentBalance'], currency, self._unit_of_measurement))
                                # _LOGGER.info('Account - {}: Converting {} {} to {} {}'.format(override_account, currency, active_account['currentBalance'], self._unit_of_measurement, converted_balance))
                                active_account['currentBalance'] = converted_balance

        # _LOGGER.info('Accounts inforrmation after currency conversion:')
        # for active_account in active_accounts:
            # _LOGGER.info('  {} ({}): {} {}'.format(active_account['accountName'], active_account['id'], self._unit_of_measurement, active_account['currentBalance']))
        active_accounts_sum = round(sum(active_account['currentBalance'] for active_account in active_accounts))
        asset_accounts_sum = round(sum(asset_account['currentBalance'] for asset_account in asset_accounts))
        liability_accounts_sum = round(sum(liability_account['currentBalance'] for liability_account in liability_accounts))

        _LOGGER.info('Mint networth: {} {}, assets: {}, liabilities: {}'.format(self._unit_of_measurement, active_accounts_sum, asset_accounts_sum, liability_accounts_sum))

        # self._state = self._mint_client.get_net_worth()
        self._state = active_accounts_sum
        self._assets = asset_accounts_sum
        self._liabilities = liability_accounts_sum

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Mint Networth'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measure this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return 'mdi:square-inc-cash'

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        attributes = {
            ATTR_ASSETS: self._assets,
            ATTR_LIABILITIES: self._liabilities
        }
        # return attributes
        return {}


class MintCategorySensor(Entity):
    """Representation of a personalcapital.com sensor."""
    last_used = time.time() - MIN_TIME_BETWEEN_UPDATES

    def __init__(self, hass, mint_client, config, sensor_type):
        """Initialize the sensor."""
        self.hass = hass
        self._mint_client = mint_client
        self._sensor_type = sensor_type
        self._productType = SENSOR_TYPES[sensor_type][0]
        self._name = 'Mint {}'.format(SENSOR_TYPES[sensor_type][1])
        self._inverse_sign = SENSOR_TYPES[sensor_type][2]
        self._state = None
        self._config = config
        self._unit_of_measurement = config[CONF_UNIT_OF_MEASUREMENT]

    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Get the latest state of the sensor."""
        # self._mint_client.initiate_account_refresh()
        _LOGGER.info('Updating mint category - {}'.format(self._sensor_type))

        data = self._mint_client.get_accounts()

        # Save new update time
        # MintNetWorthSensor.last_used = time.time()

        active_accounts = [account for account in data if account['isActive'] == True and account['isAccountNotFound'] == False and account['isClosed'] == False]
        sensor_type_accounts = [account for account in active_accounts if account['accountType'] == self._sensor_type]

        account_currency_overrides = self._config.get(CONF_ACCOUNT_CURRENCY_OVERRIDE)

        if account_currency_overrides:
            from currency_converter import CurrencyConverter
            converter = CurrencyConverter()

            for account_currency in account_currency_overrides:
                for currency in account_currency.keys():
                    override_accounts = account_currency[currency]
                    # _LOGGER.info("{}-{}".format(currency, override_accounts))
                    for override_account in override_accounts:
                        for sensor_type_account in sensor_type_accounts:
                            if sensor_type_account['id'] == override_account:
                                converted_balance = round(converter.convert(sensor_type_account['currentBalance'], currency, self._unit_of_measurement))
                                # _LOGGER.info('Account - {}: Converting {} {} to {} {}'.format(override_account, currency, sensor_type_account['currentBalance'], self._unit_of_measurement, converted_balance))
                                sensor_type_account['currentBalance'] = converted_balance

        sensor_type_accounts_sum = round(sum(sensor_type_account['currentBalance'] for sensor_type_account in sensor_type_accounts))
        sensor_type_accounts_sum = format_balance(self._inverse_sign, sensor_type_accounts_sum)
        _LOGGER.info('Mint Category - {}: {} {}'.format(self._sensor_type, self._unit_of_measurement, sensor_type_accounts_sum))
        self._state = sensor_type_accounts_sum

        self.hass.data[self._productType] = {'accounts': []}
        for account in sensor_type_accounts:
            _LOGGER.info('  ({}) {}: {} {}'.format(self._sensor_type, account['accountName'], self._unit_of_measurement, account['currentBalance']))
            self.hass.data[self._productType].get('accounts').append({
                "name": account.get('accountName', ''),
                "id": account.get('id', ''),
                "firm_name": account.get('fiName', ''),
                # "logo": account.get('logoPath', ''),
                "balance": format_balance(self._inverse_sign, account.get('currentBalance', 0.0)),
                "account_type": account.get('accountType', ''),
                # "url": account.get('homeUrl', ''),
                "currency": account.get('currency', ''),
                "refreshed": account.get('lastUpdatedInDate', ''),
                # "refreshed": how_long_ago(account.get('lastUpdatedInDate', 0)) + ' ago',
            })

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement this sensor expresses itself in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return 'mdi:coin'

    @property
    def device_state_attributes(self):
        """Return the state attributes of the sensor."""
        return self.hass.data[self._productType]

def how_long_ago(last_epoch):
    a = last_epoch
    b = datetime.now()
    c = b - a
    days = c // 86400
    hours = c // 3600 % 24
    minutes = c // 60 % 60

    if days > 0:
        return str(round(days)) + ' days'
    if hours > 0:
        return str(round(hours)) + ' hours'
    return str(round(minutes)) + ' minutes'


def format_balance(inverse_sign, balance):
    return -1.0 * balance if inverse_sign is True else balance
