{
  "title":"Provenance Container",
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
      "description":"Map of entities by ids. TODO: use patternProperties instead of additionalProperties as the keys are required to be valid ids.",
      "additionalProperties":{
        "type":"object",
        "title":"entity",
        "additionalProperties":{
          "type":"string",
          "title": "literal",
          "pattern": "TODO"
        }
      }
    },
    "activity":{
      "type":"object",
      "description":"Map of activities by ids",
      "additionalProperties":{
        "type":"object",
        "title":"activity",
        "properties":{
          "recipeLink": {"type": "string", "format": "uri"},
          "startTime": {"type": "string", "format": "date-time"},
          "endTime": {"type": "string", "format": "date-time"}
        },
        "additionalProperties":{"$ref":"literal"}
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
    "note":{
      "type":"object",
      "description":"Map of notes by ids",
      "additionalProperties":{
        "type":"object",
        "title":"entity",
        "additionalProperties":{"$ref":"literal"}
      }
    },
    "account": {
      "type":"object",
      "description":"Map of accounts by ids",
      "properties":{
        "asserter": {"type": "string", "format": "uri"},
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
        "wasComplementOf":{"$ref":"#/properties/wasComplementOf"},
        "hasAnnotation":{"$ref":"#/properties/hasAnnotation"}
      },
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
          "wasComplementOf":{"$ref":"#/properties/wasComplementOf"},
          "hasAnnotation":{"$ref":"#/properties/hasAnnotation"}
        },
        "additionalProperties": false
      }
    },
    "wasGeneratedBy": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "entity": {"type": "string", "format": "uri", "required":true},
          "activity": {"type": "string", "format": "uri", "required":true},
          "time": {"type": "string", "format": "date-time"}
        },
        "additionalProperties":{"$ref":"literal"}
      }
    },
    "used": {"$ref":"#/properties/wasGeneratedBy"},
    "wasAssociatedWith": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "activity": {"type": "string", "format": "uri", "required":true},
          "agent": {"type": "string", "format": "uri", "required":true}
        },
        "additionalProperties":{"$ref":"literal"}
      }
    },
    "wasStartedBy": {"$ref":"#/properties/wasAssociatedWith"},
    "wasEndedby": {"$ref":"#/properties/wasAssociatedWith"},
    "actedOnBehalfOf": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "subordinate": {"type": "string", "format": "uri", "required":true},
          "responsible": {"type": "string", "format": "uri", "required":true},
          "activity": {"type": "string", "format": "uri"}
        },
        "additionalProperties":{"$ref":"literal"}
      }
    },
    "wasDerivedFrom": {
      "type":"object",
      "decription":"PROV-DM requires that activity, generation, and usage must be present at the same time with one another, hence the 'dependencies' requirements below. However, the requirement for 'prov:steps' can not be described as 'prov:steps' could also appear as 'steps' or 'anyprefix:steps'",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "generatedEntity": {"type": "string", "format": "uri", "required":true},
          "usedEntity": {"type": "string", "format": "uri", "required":true},
          "activity": {"type": "string", "format": "uri"},
          "generation": {"type": "string", "format": "uri"},
          "usage": {"type": "string", "format": "uri"}
        },
        "additionalProperties":{"$ref":"literal"},
        "dependencies": {
          "activity": ["generation", "usage"],
          "generation": ["activity", "usage"],
          "usage": ["activity", "generation"]
        }
      }
    },
    "wasComplementOf": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "subject": {"type": "string", "format": "uri", "required":true},
          "alternate": {"type": "string", "format": "uri", "required":true}
        },
        "additionalProperties": false
      }
    },
    "hasAnnotation": {
      "type":"object",
      "additionalProperties":{
        "type":"object",
        "properties":{
          "annotated": {"type": "string", "format": "uri", "required":true},
          "note": {"type": "string", "format": "uri", "required":true}
        },
        "additionalProperties": false
      }
    }
    
  },
  "additionalProperties": false
}
