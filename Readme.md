# Home Assistant Custom Components

## Mint Finance
Custom component for [Mint Finance](https://www.mint.com/)

This currently only works in a non `HEADLESS` mode due to limitations of the dependency it uses.

### Configuration:

```yaml
sensor:
  - platform: mint_finance
    username: !secret mint_username
    password: !secret mint_password
    monitored_categories:
      - investment
      - bank
      - 'other property'
      - credit
    unit_of_measurement: USD
    account_currency_override:
      CAD: !secret mint_cad_account_list
      INR: !secret mint_cad_account_list
```

#### Configuration variables
- **username**: Your mint account username
- **password**: Your mint account password
- **monitored_categories** (Optional): List of categories you'd like to monitor. Available options are investment, bank, other property, credit, mortgage, loan, real estate, vehicle and unclassified.
- **unit_of_measurement** (Optional): Default is `USD`.
- **account_currency_override** (Optional): Mint only supports one currency, so your accounts from multiple different currencies will report numeric value in same currency as is instead of performing any currency conversions. With this option, you can provide list of accounts you'd like to covert into default `unit_of_measurement`
- **exclude_accounts** (Optional): List of accounts you'd like to exclude. We exclude accounts which are not active always. This option allows excluding any additional accounts you don't want to see in home assistant.

## Setup
### Custom Updater
[custom_components.json](./custom_components.json) provides the details Custom Updater needs. See [Custom Updater Installation](https://github.com/custom-components/custom_updater/wiki/Installation) to install it.

Add the following to your configuration:
```
custom_updater:
  track:
    - components
  component_urls:
    - https://raw.githubusercontent.com/sanghviharshit/homeassistant-custom/master/custom_components.json
```

## Installation
To install one of these custom components, use the [`custom_updater.install`](https://github.com/custom-components/custom_updater/wiki/Services#install-element-cardcomponentpython_script) service with appropriate service data, such as:
```
{
  "element": "sensor.mint_finance"
}
```


[![Analytics](https://ga-beacon.appspot.com/UA-59542024-4/homeassistant-custom/)](https://github.com/igrigorik/ga-beacon)
