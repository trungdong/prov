{
  "title":"Provenance Bundle",
  "type":"object",
  
  "properties":{
    "prefix":{
      "type":"object",
      "description":"",
      "patternProperties": {
        "^[a-zA-Z0-9_\\-]+$": {
          "type" : "string",
          "format": "uri"
        }
      },
      "additionalProperties":false
    },
    "entity":{
      "type":"object",
      "description":"Map of entities by ids",
	  // TODO: use patternProperties instead of additionalProperties as the keys are required to be valid ids (i.e. following a specific pattern).
      "additionalProperties":{
        "type":"object",
        "title":"entity",
		// TODO: Define the schema for attribute-value pairs here and the other similar occurences in the objects below, taking into account qname id, literals, and provjs:array datatypes
        "additionalProperties":{}
      }
    },
    "activity":{
      "type":"object",
      "description":"Map of activities by ids",
      "additionalProperties":{
        "type":"object",
        "title":"activity",
        "properties":{
          "prov:startTime": {"type": "string", "format": "date-time"},
          "prov:endTime": {"type": "string", "format": "date-time"}
        },
		"additionalProperties":{"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "agent":{
      "type":"array",
      "description":"List of ids of entities that are assert as agents",
      "items":{
        "type":"string",
        "format": "uri"
      }
    },
    "bundle": {
      "type":"object",
      "description":"Map of named bundles by ids",
      "additionalProperties": {
        "type":"object",
        "title":"account",
        "properties":{
          "asserter": {"type": "string", "format": "uri", "required": true},
          "entity":{"$ref":"#/properties/entity"},
          "activity":{"$ref":"#/properties/activity"},
          "agent":{"$ref":"#/properties/agent"},
          "note":{"$ref":"#/properties/note"},
          "wasGeneratedBy":{"$ref":"#/properties/wasGeneratedBy"},
          "used":{"$ref":"#/properties/used"},
          "wasAssociatedWith":{"$ref":"#/properties/wasAssociatedWith"},
          "wasStartedBy":{"$ref":"#/properties/wasStartedBy"},
          "wasEndedby":{"$ref":"#/properties/wasEndedby"},
          "actedOnBehalfOf":{"$ref":"#/properties/actedOnBehalfOf"},
          "wasDerivedFrom":{"$ref":"#/properties/wasDerivedFrom"},
          "alternateOf":{"$ref":"#/properties/alternateOf"},
          "specializationOf":{"$ref":"#/properties/specializationOf"},
          "hasAnnotation":{"$ref":"#/properties/hasAnnotation"},
		  "account": {"$ref":"#/properties/account"}
        },
		"additionalProperties": {"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "wasGeneratedBy": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:entity": {"type": "string", "format": "uri", "required":true},
          "prov:activity": {"type": "string", "format": "uri", "required":true},
          "prov:time": {"type": "string", "format": "date-time"}
        },
        "additionalProperties":{"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "used": {"$ref":"#/properties/wasGeneratedBy"},
    "wasAssociatedWith": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:activity": {"type": "string", "format": "uri", "required":true},
          "prov:agent": {"type": "string", "format": "uri", "required":true},
          "prov:plan": {"type": "string", "format": "uri", "required":false}
        },
        "additionalProperties":{"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "wasStartedBy": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:activity": {"type": "string", "format": "uri", "required":true},
          "prov:agent": {"type": "string", "format": "uri", "required":true}
        },
        "additionalProperties":{"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "wasEndedby": {"$ref":"#/properties/wasStartedBy"},
    "actedOnBehalfOf": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:subordinate": {"type": "string", "format": "uri", "required":true},
          "prov:responsible": {"type": "string", "format": "uri", "required":true},
          "prov:activity": {"type": "string", "format": "uri"}
        },
        "additionalProperties":{"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "wasDerivedFrom": {
      "type":"object",
      "decription":"PROV-DM requires that activity, generation, and usage must be present at the same time with one another, hence the 'dependencies' requirements below. However, the requirement for 'prov:steps' can not be described as 'prov:steps' could also appear as 'steps' or 'anyprefix:steps'",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:generatedEntity": {"type": "string", "format": "uri", "required":true},
          "prov:usedEntity": {"type": "string", "format": "uri", "required":true},
          "prov:activity": {"type": "string", "format": "uri"},
          "prov:generation": {"type": "string", "format": "uri"},
          "prov:usage": {"type": "string", "format": "uri"}
        },
        "additionalProperties":{"$ref":"#/properties/entity/additionalProperties/additionalProperties"},
        "dependencies": {
          "prov:activity": ["prov:generation", "prov:usage"],
          "prov:generation": ["prov:activity", "prov:usage"],
          "prov:usage": ["prov:activity", "prov:generation"]
        }
      }
    },
    "alternateOf": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:entity": {"type": "string", "format": "uri", "required":true},
          "prov:alternate": {"type": "string", "format": "uri", "required":true}
        },
        "additionalProperties": {"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },
    "specializationOf": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "prov:entity": {"type": "string", "format": "uri", "required":true},
          "prov:specialization": {"type": "string", "format": "uri", "required":true}
        },
        "additionalProperties": {"$ref":"#/properties/entity/additionalProperties/additionalProperties"}
      }
    },    
  },
  "additionalProperties": false
}
