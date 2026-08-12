# TICKR Plugin Development

Develop indicator and scanner plugins here, build them into a `.zip`, and
install them into a running TICKR app through **Profile → Admin → Plugins**.
No backend code changes or restarts are needed to add a new plugin.

```
plugin-dev/
  indicators/<your_plugin>/manifest.json + plugin.py
  scanners/<your_plugin>/manifest.json + plugin.py
  plugin_sdk.py     # dev-time stub so imports resolve in your editor (see below)
  build.py          # packages a plugin folder into dist/*.zip
  dist/             # build output — upload these .zip files via the admin UI
```

## Writing an indicator plugin

Create `indicators/my_indicator/manifest.json`:

```json
{
  "name": "MY_IND",
  "type": "indicator",
  "version": "1.0.0",
  "description": "What this indicator shows",
  "author": "you",
  "entry_module": "plugin",
  "entry_class": "MyIndicator"
}
```

`entry_module` is the `.py` filename (without `.py`) inside your plugin folder
that defines `entry_class`. They can be named anything, as long as the
manifest points at them correctly — `plugin.py` / `MyIndicator` is just a
convention.

Create `indicators/my_indicator/plugin.py`:

```python
import pandas as pd
from plugin_sdk import BaseIndicator

class MyIndicator(BaseIndicator):
    name = "MY_IND"                  # must match manifest.json's "name"
    label = "MY_IND({period})"       # shown in the indicator pill, with params filled in
    description = "What this indicator shows"
    category = "momentum"            # trend | momentum | volatility | volume
    overlay = False                  # True = drawn on the price chart; False = its own sub-chart panel below the volume bars
    default_params = {"period": 14}
    param_schema = [
        {"name": "period", "type": "int", "min": 2, "max": 100, "label": "Period"},
    ]

    def compute(self, df: pd.DataFrame, **params) -> pd.DataFrame:
        # df has columns: date, open, high, low, close, volume
        period = int(params.get("period", self.default_params["period"]))
        df = df.copy()
        df[f"MY_IND_{period}"] = df["close"].rolling(period).mean()  # replace with real logic
        return df
```

See `indicators/rsi/` for a complete, real example (also the one TICKR ships
pre-installed).

## Writing a scanner plugin

Same shape, under `scanners/<name>/`, but the entry class subclasses
`BaseScanner` and implements `run(symbols, exchange, as_of_date, **params) ->
list[dict]` instead of `compute()`. Each result dict needs at minimum
`{symbol, exchange, price, change_pct}` plus whatever scan-specific fields
you want to surface.

## Building

```bash
cd plugin-dev
python build.py indicators/rsi
# -> dist/rsi-indicator-1.0.0.zip
```

The build script validates your `manifest.json` and that the entry module
exists before zipping — it won't produce a broken artifact.

## Installing

In the TICKR app: **Profile → Admin → Plugins → Upload**, pick the `.zip`
from `dist/`. It's validated, extracted, and registered immediately — no
server restart. From then on it shows up in the Indicator/Scanner dropdown
like any built-in one. Re-uploading the same plugin `name` + `type` replaces
the previous version in place (useful for iterating).

Enable/disable/delete are also on that same Admin page.

## The `plugin_sdk` import

Inside `plugin.py` you always write `from plugin_sdk import BaseIndicator` (or
`BaseScanner`) — never reach into TICKR's internal `app.*` modules. The
`plugin_sdk.py` file sitting next to this README is a **dev-time stub**: it
exists purely so your editor/linter resolves the import while you're working
in this folder. It is not packaged into your `.zip` and has no effect at
runtime. When TICKR actually loads your installed plugin, it binds the
`plugin_sdk` name to its own real `BaseIndicator`/`BaseScanner` classes — that
binding is what your plugin actually runs against.

## Security

Installing a plugin runs its Python code with full server privileges — there
is no sandboxing. Only build and install plugins you wrote yourself or fully
trust, exactly as you'd vet any other dependency added to this codebase.
