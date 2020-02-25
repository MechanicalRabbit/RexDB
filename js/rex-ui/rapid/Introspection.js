/**
 * @flow
 */
import invariant from "invariant";
import * as introspection from "graphql/utilities/introspectionQuery";
import * as ast from "graphql/language/ast";
import { print } from "graphql/language/printer";
import * as QueryPath from "./QueryPath.js";
import * as Field from "./Field.js";
import { ConfigError } from "./ErrorBoundary";
import { buildSortingConfig } from "./buildSortingConfig.js";

export type TypeIntrospectionFieldType = {|
  kind: string,
  name: ?string,
  ofType: ?TypeIntrospectionFieldType,
|};

export type TypeIntrospectionTypesMap = {
  [key: string]: introspection.IntrospectionType,
};

export type TypeSchemaDataObject = {|
  schema: introspection.IntrospectionSchema,
  typesMap: Map<string, introspection.IntrospectionType>,
|};

type QueryFieldSpec = {
  field: string,
  require?: Array<QueryFieldSpec>,
};

export type Introspection<T: { [name: string]: Field.FieldSpec }> = {|
  query: string,
  fieldSpecs: T,
  filterSpecs: ?Field.FilterSpecMap,
  description?: ?string,
  sortingConfig: ?Array<{| desc: boolean, field: string |}>,
  variablesMap: ?Map<string, Field.VariableDefinition>,
|};

export type IntrospectionConfig<T: { [name: string]: Field.FieldConfig }> = {|
  schema: introspection.IntrospectionSchema,
  path: QueryPath.QueryPath,
  fields?: ?T,
  filters?: ?Array<Field.FilterConfig>,
|};

/**
 * Introspect GraphQL schema.
 */
export function introspect<T: { [name: string]: Field.FieldConfig }>({
  schema,
  path,
  fields,
  filters,
}: IntrospectionConfig<T>): Introspection<
  $ObjMap<T, <V>(V) => Field.FieldSpec>,
> {
  const fieldSpecs = Field.configureFields(fields);
  const filterSpecs = Field.configureFilters(filters);

  const {
    ast,
    introspectionTypesMap,
    fieldSpecsUpdated,
    description,
    queryDefinition,
  } = buildQueryAST(schema, path, fieldSpecs);

  const sortingConfig = buildSortingConfig({
    variableDefinitions: queryDefinition.variableDefinitions,
    fieldSpecs: fieldSpecsUpdated,
    introspectionTypesMap,
    filterSpecs,
  });

  let variablesMap = null;
  if (
    queryDefinition.variableDefinitions &&
    queryDefinition.variableDefinitions.length > 0
  ) {
    variablesMap = new Map();
    for (let variable of queryDefinition.variableDefinitions) {
      variablesMap.set(variable.variable.name.value, variable);
    }
  }

  const query = print(ast);
  return {
    query,
    fieldSpecs: fieldSpecsUpdated,
    description,
    filterSpecs,
    sortingConfig,
    variablesMap,
  };
}

export const buildQueryAST = (
  schema: introspection.IntrospectionSchema,
  path: QueryPath.QueryPath,
  fieldSpecsRequested: ?{ [name: string]: Field.FieldSpec },
): {|
  ast: ast.DocumentNode,
  columns: ast.FieldNode[],
  introspectionTypesMap: Map<string, introspection.IntrospectionType>,
  queryDefinition: ast.OperationDefinitionNode,
  fieldSpecsUpdated: { [name: string]: Field.FieldSpec },
  description: ?string,
|} => {
  let typesMap: Map<string, introspection.IntrospectionType> = new Map();
  for (let t of schema.types) {
    typesMap.set(t.name, t);
  }

  let rootType = typesMap.get(schema.queryType.name);
  if (rootType == null) {
    throw new ConfigError("Expected ObjectType at the root");
  }
  if (rootType.kind !== "OBJECT") {
    throw new ConfigError("Expected rootType as OBJECT at the root");
  }

  let [
    selectionSet,
    columns,
    inputValues,
    fieldSpecsUpdated,
    fieldDescription,
  ] = buildSelectionSet(
    typesMap,
    rootType,
    QueryPath.toArray(path),
    fieldSpecsRequested,
  );

  const operationDefinition = {
    directives: [],
    kind: "OperationDefinition",
    name: { kind: "Name", value: "ConstructedQuery" },
    operation: "query",
    selectionSet,
    variableDefinitions: inputValues.map(buildVariableDefinitionNode),
  };

  return {
    ast: {
      kind: "Document",
      definitions: [operationDefinition],
    },
    columns,
    introspectionTypesMap: typesMap,
    queryDefinition: operationDefinition,
    fieldSpecsUpdated,
    description: fieldDescription,
  };
};

/**
 * Field.QueryFieldSpec -> void | ast.SelectionSetNode recursively
 */
export const makeSelectionSetFromQueryFieldSpec = (
  queryFieldSpec: Field.QueryFieldSpec,
): ast.SelectionSetNode => {
  let selections = [];

  if (queryFieldSpec.require != null) {
    for (let query of queryFieldSpec.require) {
      selections.push({
        kind: "Field",
        name: {
          kind: "Name",
          value: query.field,
        },
        selectionSet: makeSelectionSetFromQueryFieldSpec(query),
      });
    }
  }

  return {
    kind: "SelectionSet",
    selections,
  };
};

/**
 * Builds SelectionSet using makeSelectionSetFromQueryFieldSpec recursion
 */
export const makeSelectionSetFromSpec = (
  fieldSpec: Field.FieldSpec,
): ast.SelectionSetNode => {
  let selections = [];
  if (fieldSpec.require.require != null) {
    for (let obj of fieldSpec.require.require) {
      selections.push({
        kind: "Field",
        name: {
          kind: "Name",
          value: obj.field,
        },
        selectionSet: makeSelectionSetFromQueryFieldSpec(obj),
      });
    }
  }

  return {
    kind: "SelectionSet",
    selections,
  };
};

export const buildSelectionSet = (
  typesMap: Map<string, introspection.IntrospectionType>,
  type: introspection.IntrospectionObjectType,
  path: string[],
  fieldSpecsRequested: ?{ [name: string]: Field.FieldSpec },
): [
  ast.SelectionSetNode,
  ast.FieldNode[],
  introspection.IntrospectionInputValue[],
  { [name: string]: Field.FieldSpec },
  ?string,
] => {
  // Break the recursion
  if (path.length === 0) {
    let fieldSpecsMap = new Map<string, Field.FieldSpec>();
    let fieldIntros: introspection.IntrospectionField[] = [];
    let fieldSpecs: { [name: string]: Field.FieldSpec } = {};

    if (fieldSpecsRequested != null) {
      for (let name in fieldSpecsRequested) {
        let fieldSpec = fieldSpecsRequested[name];
        fieldSpecsMap.set(fieldSpec.require.field, fieldSpec);
      }

      fieldSpecs = fieldSpecsRequested;
      fieldIntros = type.fields.filter(field => {
        return fieldSpecsMap.get(field.name) || field.name === "id";
      });
    } else {
      for (let field of type.fields) {
        if (!isFieldNodeScalarLike(field)) {
          continue;
        }
        const spec = {
          title: Field.guessFieldTitle(field.name),
          require: { field: field.name },
        };

        fieldIntros.push(field);
        fieldSpecsMap.set(field.name, spec);
      }

      let COMMON_NAMES = [
        "id",
        "name",
        "first_name",
        "last_name",
        "title",
        "display_name",
        "gender",
        "sex",
      ];

      let seen = new Set();
      for (let name of COMMON_NAMES) {
        let spec = fieldSpecsMap.get(name);
        if (spec == null) {
          continue;
        }
        fieldSpecs[name] = spec;
        seen.add(name);
      }

      for (let spec of fieldSpecsMap.values()) {
        if (!seen.has(spec.require.field)) {
          fieldSpecs[spec.require.field] = spec;
        }
      }
    }

    const selections: ast.FieldNode[] = [];
    const inputValues: introspection.IntrospectionInputValue[] = [];

    for (let field of fieldIntros) {
      let args = [];
      for (let arg of field.args) {
        args.push(buildArgumentNode(arg));
        inputValues.push(arg);
      }

      let fieldSpec = fieldSpecsMap.get(field.name);
      if (fieldSpec == null) {
        if (field.name === "id") {
          fieldSpec = { title: "ID", require: { field: "id" } };
        } else {
          throw new ConfigError(`Missing field spec for ${field.name}`);
        }
      }

      const selectionSet = makeSelectionSetFromSpec(fieldSpec);

      selections.push({
        kind: "Field",
        arguments: args,
        directives: [],
        name: { kind: "Name", value: field.name },
        selectionSet,
      });
    }

    let selectionSet = {
      kind: "SelectionSet",
      selections,
    };

    return [selectionSet, selections, inputValues, fieldSpecs, null];
  } else {
    const [fieldName, ...restPath] = path;
    const [field, fieldType] = resolveField(typesMap, type, fieldName);

    const args = [];
    const inputValues = [];
    for (let arg of field.args) {
      args.push(buildArgumentNode(arg));
      inputValues.push(arg);
    }

    const [
      selectionSet,
      selections,
      nextInputValues,
      fieldSpecs,
    ] = buildSelectionSet(typesMap, fieldType, restPath, fieldSpecsRequested);

    const ast = {
      kind: "SelectionSet",
      selections: [
        {
          arguments: args,
          directives: [],
          kind: "Field",
          name: { kind: "Name", value: fieldName },
          selectionSet,
        },
      ],
    };
    return [
      ast,
      selections,
      inputValues.concat(nextInputValues),
      fieldSpecs,
      field.description,
    ];
  }
};

const buildArgumentNode = (
  introInputValue: introspection.IntrospectionInputValue,
): ast.ArgumentNode => {
  let name: ast.NameNode = {
    kind: "Name",
    value: introInputValue.name,
  };

  let value: ast.ValueNode = {
    kind: "Variable",
    name: {
      kind: "Name",
      value: introInputValue.name,
    },
  };

  return {
    kind: "Argument",
    name,
    value,
  };
};

const buildVariableDefinitionNode = (
  introInputValue: introspection.IntrospectionInputValue,
): ast.VariableDefinitionNode => {
  return {
    kind: "VariableDefinition",
    variable: {
      kind: "Variable",
      name: {
        kind: "Name",
        value: introInputValue.name,
      },
    },
    type: buildTypeNode(introInputValue.type),
  };
};

const buildTypeNode = (
  introType: introspection.IntrospectionInputTypeRef,
): ast.TypeNode => {
  switch (introType.kind) {
    case "NON_NULL": {
      let type = buildTypeNode(introType.ofType);
      invariant(
        type.kind === "ListType" || type.kind === "NamedType",
        "Nested NonNullType is not possible",
      );
      return {
        kind: "NonNullType",
        type,
      };
    }
    case "LIST": {
      return {
        kind: "ListType",
        type: buildTypeNode(introType.ofType),
      };
    }
    case "INPUT_OBJECT":
      return {
        kind: "NamedType",
        name: { kind: "Name", value: introType.name },
      };
    case "ENUM":
      return {
        kind: "NamedType",
        name: { kind: "Name", value: introType.name },
      };
    case "SCALAR":
      return {
        kind: "NamedType",
        name: { kind: "Name", value: introType.name },
      };
    default:
      // (introType.kind: empty);
      invariant(false, `Unknown GraphQL introspection type: ${introType.kind}`);
  }
};

function isFieldNodeScalarLike(field) {
  return (
    field.type.kind === "SCALAR" ||
    (field.type.kind === "NON_NULL" && field.type.ofType.kind === "SCALAR")
  );
}

function isFieldNodeObjectLike(field) {
  return (
    field.type.kind === "OBJECT" ||
    (field.type.kind === "NON_NULL" && field.type.ofType.kind === "OBJECT")
  );
}

function isFieldNodeListLike(field) {
  return (
    field.type.kind === "LIST" ||
    (field.type.kind === "NON_NULL" && field.type.ofType.kind === "LIST")
  );
}

export const resolveField = (
  typesMap: Map<string, introspection.IntrospectionType>,
  type: introspection.IntrospectionObjectType,
  fieldName: string,
): [
  introspection.IntrospectionField,
  introspection.IntrospectionObjectType,
] => {
  const field = type.fields.find(f => f.name === fieldName);
  if (field == null) {
    throw new ConfigError(`No field "${type.name}.${fieldName}" found`);
  }

  function resolveType(typeRef) {
    let nextType;
    switch (typeRef.kind) {
      case "NON_NULL":
        nextType = resolveType(typeRef.ofType);
        break;
      case "LIST":
        nextType = resolveType(typeRef.ofType);
        break;
      case "ENUM":
        nextType = typesMap.get(typeRef.name);
        break;
      case "SCALAR":
        break;
      case "UNION":
        nextType = typesMap.get(typeRef.name);
        break;
      case "INTERFACE":
        nextType = typesMap.get(typeRef.name);
        break;
      case "OBJECT":
        nextType = typesMap.get(typeRef.name);
        break;
      default:
        // (typeRef.kind: empty);
        invariant(false, "Impossible");
    }
    invariant(
      nextType != null,
      `No type for field "${type.name}.${fieldName}" found`,
    );
    return nextType;
  }

  let nextType = resolveType(field.type);

  if (nextType.kind !== "OBJECT") {
    throw new ConfigError("Expected object type for nextType.kind");
  }
  return [field, nextType];
};
