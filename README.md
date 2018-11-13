# Launching

### Installing virtualenv

```
cd hypergrc
virtualenv venv
source venv/bin/activate
pip install flask
pip install python-dotenv
pip install flask_wtf
pip install rtyaml
pip install Flask-Testing
export FLASK_APP=hypergrc.py
export GOVREADY_FILE=/abs/path/to/.govready

# Force reload upon code changes
export FLASK_DEBUG=1

flask run
```

### Running Flask server
```
cd hypergrc

# If venv not active
source venv/bin/activate

# If not run in a while
export FLASK_APP=hypergrc.py

# Force reload upon code changes
export FLASK_DEBUG=1

# Path to .govready file
export GOVREADY_FILE=/abs/path/to/.govready

flask run
```

# Licensing

hyperGRC is copyrighted 2018 by GovReady PBC and available under the open source license indicated in [LICENSE.md](LICENSE.md).

