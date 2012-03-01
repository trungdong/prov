var _flatten = function(flattened, json) {
	if (json instanceof Array) {
		json.forEach(function(j) { _flatten(flattened, j); });
	}
	else if (typeof(json) === "object") {
		for (key in json) {
			if(key === "__key") continue;
			value = json[key];
			if (value===null || !(value instanceof Array || typeof(value) === "object")) continue;
			value.__key = key;
			flattened.push(value);
			_flatten(flattened, value);
		}
	}
};

var _arrayify = function(obj) {
	var result = [];
	if (obj instanceof Array) {
		result = result.concat(obj);
	}
	else if (typeof(obj) === "object") {
		for (key in obj) {
			if (key === "__key") continue;
			result.push(obj[key]);
		}
	}
	else {
		result = obj;
	}
	return result;
};

var _matches = function(a, b) {
	if(a instanceof Array && b instanceof Array) {
		if (a.length !== b.length)
			return false;
		else {
		    for (var i = 0; i < a.length; i++) {
		        if (!_matches(a[i], b[i])) return false;
		    }
			return true;
		}
	}
	if (typeof(b) === "object" && b[a]) {
		return true;
	}
	if (b == a) {
		return true;
	}

	return false;
};


IndexedJSON = function(json) {
	this.__data = [];
	if (json) {
		if (json === null) return this; 
		if (json instanceof Array) {
			json.forEach(function(j) { _flatten(this.__data, j); });
		}
		else {
			this.__data.push(json);
			_flatten(this.__data, json);
		}
	}
	return this;
};

IndexedJSON.prototype.get = function(key, value) {
	if (value) {
		filtered = this.filter(key, value);
		return filtered.__data[0];
	}
	else {
		if (!this.__index) {
			var index = {};
			this.__data.forEach(function(obj) {
				if ("__key" in obj) {
					index[obj.__key] = obj;
				}
			});
			this.__index = index;
		}
		if (key in this.__index) return this.__index[key];
		else return null;
	}
};

IndexedJSON.prototype.getKeyOf = function(key, value) {
	filtered = this.filter(key, value);
	return filtered.__data[0].__key;
};

IndexedJSON.prototype.values = function(key) {
	var result = [];
	if (key) {
		this.__data.forEach(function(obj) {
			if (obj[key]) {
				result = result.concat(_arrayify(obj[key]));
			}
		});
	}
	else {
		result = result.concat(this.__data);
	}
	return result;
};

IndexedJSON.prototype.keys = function(key) {
	var result = [];
	if (!key) {
		this.__data.forEach(function(obj) {
			if ("__key" in obj)
				result.push(obj.__key);
		});
	}
	else 
		this.__data.forEach(function(obj) {
			if (key in obj) {
				for (k in obj[key]) {
					if (k !== "__key")
						result.push(k);
				}
			}
		});
	
	return result;
};

IndexedJSON.prototype.filter = function(key, value) {
	var result = [];
	this.__data.forEach(function(obj) {
		if (obj[key]) {
			if (!value || _matches(obj[key], value)) {
				result.push(obj);
			}
		}
	});
	ijson = new IndexedJSON();
	ijson.__data = result;
	return ijson;
};

IndexedJSON.prototype.filterValue = function(value) {
	var result = [];
	this.__data.forEach(function(obj) {
		for (key in obj) {
			if (key === "__key") continue;
			if (_matches(obj[key], value)) {
				result.push(obj);
			}
		}
	});
	ijson = new IndexedJSON();
	ijson.__data = result;
	return ijson;
};

IndexedJSON.prototype.childrenOf = function(key) {
	var result = [];
	this.__data.forEach(function(obj) {
		if (obj[key]) {
			result = result.concat(_arrayify(obj[key]));
		}
	});
	ijson = new IndexedJSON();
	ijson.__data = result;
	return ijson;
};
IndexedJSON.prototype.in = IndexedJSON.prototype.childrenOf;