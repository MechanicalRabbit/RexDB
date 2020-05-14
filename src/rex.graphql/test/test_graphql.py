import pytest

from rex.graphql import (
    Entity,
    Record,
    Object,
    List,
    scalar,
    entity_id,
    NonNull,
    Enum,
    EnumValue,
    q,
    query,
    connect,
    compute,
    argument,
    InputObject,
    InputObjectField,
    param,
    parent_param,
    schema,
    execute,
    filter_from_function,
    compute_from_function,
    mutation_from_function,
)
from rex.core import Rex, Error
from rex.db import get_db


@pytest.fixture(scope="module")
def rex():
    # Create Rex instance for all tests.
    db = "pgsql:graphql_demo"
    rex = Rex("rex.graphql_demo", db=db)
    return rex


@pytest.fixture(autouse=True)
def with_rex(rex):
    with rex:
        yield


def get_simple_schema():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "comment": query(q.comment),
            "nation_list": query(q.nation, nation),
            "nation_count": query(q.nation.count()),
        },
    )
    nation = Entity(
        "nation",
        fields=lambda: {
            "name": query(q.name),
            "comment": query(q.comment),
            "region": query(q.region, region),
        },
    )
    return schema(
        fields=lambda: {
            "nation": query(q.nation, nation),
            "region": query(q.region, region),
            "africa": query(q.region.filter(q.name == "AFRICA"), region),
        }
    )


def test_simple():
    sch = get_simple_schema()
    data = execute(
        sch,
        """
        query {
            region { name }
            nation { name }
        }
        """,
    ).data
    assert data == {
        "nation": [
            {"name": "ALGERIA"},
            {"name": "ARGENTINA"},
            {"name": "BRAZIL"},
            {"name": "CANADA"},
            {"name": "CHINA"},
            {"name": "EGYPT"},
            {"name": "ETHIOPIA"},
            {"name": "FRANCE"},
            {"name": "GERMANY"},
            {"name": "INDIA"},
            {"name": "INDONESIA"},
            {"name": "IRAN"},
            {"name": "IRAQ"},
            {"name": "JAPAN"},
            {"name": "JORDAN"},
            {"name": "KENYA"},
            {"name": "MOROCCO"},
            {"name": "MOZAMBIQUE"},
            {"name": "PERU"},
            {"name": "ROMANIA"},
            {"name": "RUSSIA"},
            {"name": "SAUDI ARABIA"},
            {"name": "UNITED KINGDOM"},
            {"name": "UNITED STATES"},
            {"name": "VIETNAM"},
        ],
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ],
    }


def test_compute_from_function():
    @compute_from_function()
    def add(x: scalar.Int, y: scalar.Int) -> scalar.Int:
        return x + y

    sch = schema(fields=lambda: {"add": add})

    data = execute(
        sch,
        """
        query {
            add(x: 1, y: 2)
        }
        """,
    ).data
    assert data == {"add": 3}


def test_compute_from_function_arg():
    # We define a compute field with compute_from_function with arguments
    # annotated with gql arguments. That way we can control the names of gql
    # arguments and map them to names internal to functions.
    @compute_from_function()
    def add(
        x: argument("a", scalar.Int), y: argument("b", scalar.Int)
    ) -> scalar.Int:
        return x + y

    sch = schema(fields=lambda: {"add": add})

    data = execute(
        sch,
        """
        query {
            add(a: 1, b: 2)
        }
        """,
    ).data
    assert data == {"add": 3}


def test_compute_from_function_with_parent():
    Number = Object(name="Number", fields=lambda: {"add": add})

    @compute_from_function()
    def add(forthytwo: parent_param, x: scalar.Int) -> scalar.Int:
        return forthytwo + x

    @compute_from_function()
    def forthytwo() -> Number:
        return 42

    sch = schema(fields=lambda: {"forthytwo": forthytwo})

    data = execute(
        sch,
        """
        query {
            forthytwo {
                add(x: 10)
            }
        }
        """,
    ).data
    assert data == {"forthytwo": {"add": 52}}


def test_related():
    sch = get_simple_schema()
    data = execute(
        sch,
        """
        query {
            nation {
                name
                region {
                    name
                }
            }
        }
        """,
    ).data
    assert data == {
        "nation": [
            {"name": "ALGERIA", "region": {"name": "AFRICA"}},
            {"name": "ARGENTINA", "region": {"name": "AMERICA"}},
            {"name": "BRAZIL", "region": {"name": "AMERICA"}},
            {"name": "CANADA", "region": {"name": "AMERICA"}},
            {"name": "CHINA", "region": {"name": "ASIA"}},
            {"name": "EGYPT", "region": {"name": "MIDDLE EAST"}},
            {"name": "ETHIOPIA", "region": {"name": "AFRICA"}},
            {"name": "FRANCE", "region": {"name": "EUROPE"}},
            {"name": "GERMANY", "region": {"name": "EUROPE"}},
            {"name": "INDIA", "region": {"name": "ASIA"}},
            {"name": "INDONESIA", "region": {"name": "ASIA"}},
            {"name": "IRAN", "region": {"name": "MIDDLE EAST"}},
            {"name": "IRAQ", "region": {"name": "MIDDLE EAST"}},
            {"name": "JAPAN", "region": {"name": "ASIA"}},
            {"name": "JORDAN", "region": {"name": "MIDDLE EAST"}},
            {"name": "KENYA", "region": {"name": "AFRICA"}},
            {"name": "MOROCCO", "region": {"name": "AFRICA"}},
            {"name": "MOZAMBIQUE", "region": {"name": "AFRICA"}},
            {"name": "PERU", "region": {"name": "AMERICA"}},
            {"name": "ROMANIA", "region": {"name": "EUROPE"}},
            {"name": "RUSSIA", "region": {"name": "EUROPE"}},
            {"name": "SAUDI ARABIA", "region": {"name": "MIDDLE EAST"}},
            {"name": "UNITED KINGDOM", "region": {"name": "EUROPE"}},
            {"name": "UNITED STATES", "region": {"name": "AMERICA"}},
            {"name": "VIETNAM", "region": {"name": "ASIA"}},
        ]
    }


def test_rev_related():
    sch = get_simple_schema()
    data = execute(
        sch,
        """
        query {
            region {
                name
                nation_list {
                    name
                }
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {
                "name": "AFRICA",
                "nation_list": [
                    {"name": "ALGERIA"},
                    {"name": "ETHIOPIA"},
                    {"name": "KENYA"},
                    {"name": "MOROCCO"},
                    {"name": "MOZAMBIQUE"},
                ],
            },
            {
                "name": "AMERICA",
                "nation_list": [
                    {"name": "ARGENTINA"},
                    {"name": "BRAZIL"},
                    {"name": "CANADA"},
                    {"name": "PERU"},
                    {"name": "UNITED STATES"},
                ],
            },
            {
                "name": "ASIA",
                "nation_list": [
                    {"name": "CHINA"},
                    {"name": "INDIA"},
                    {"name": "INDONESIA"},
                    {"name": "JAPAN"},
                    {"name": "VIETNAM"},
                ],
            },
            {
                "name": "EUROPE",
                "nation_list": [
                    {"name": "FRANCE"},
                    {"name": "GERMANY"},
                    {"name": "ROMANIA"},
                    {"name": "RUSSIA"},
                    {"name": "UNITED KINGDOM"},
                ],
            },
            {
                "name": "MIDDLE EAST",
                "nation_list": [
                    {"name": "EGYPT"},
                    {"name": "IRAN"},
                    {"name": "IRAQ"},
                    {"name": "JORDAN"},
                    {"name": "SAUDI ARABIA"},
                ],
            },
        ]
    }


def test_aggregate():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "nation_count": query(q.nation.count()),
        },
    )
    sch = schema(fields=lambda: {"region": query(q.region, region)})

    data = execute(
        sch,
        """
        query {
            region {
                name
                nation_count
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA", "nation_count": 5},
            {"name": "AMERICA", "nation_count": 5},
            {"name": "ASIA", "nation_count": 5},
            {"name": "EUROPE", "nation_count": 5},
            {"name": "MIDDLE EAST", "nation_count": 5},
        ]
    }


def test_field_rename():
    region = Entity("region", fields=lambda: {"region_name": query(q.name)})
    sch = schema(fields=lambda: {"region": query(q.region, region)})
    data = execute(
        sch,
        """
        query {
            region {
                region_name
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"region_name": "AFRICA"},
            {"region_name": "AMERICA"},
            {"region_name": "ASIA"},
            {"region_name": "EUROPE"},
            {"region_name": "MIDDLE EAST"},
        ]
    }


def test_filter():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "nation_count": query(q.nation.count()),
        },
    )
    sch = schema(
        fields=lambda: {
            "africa": query(q.region.filter(q.name == "AFRICA"), region)
        }
    )
    data = execute(
        sch,
        """
        query {
            africa {
                name
                nation_count
            }
        }
        """,
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}


def test_field_alias():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "nation_count": query(q.nation.count()),
        },
    )
    sch = schema(
        fields=lambda: {
            "africa": query(q.region.filter(q.name == "AFRICA"), region)
        }
    )
    data = execute(
        sch,
        """
        query {
            africa {
                africa_name: name
                nation_count
            }
        }
        """,
    ).data
    assert data == {"africa": [{"africa_name": "AFRICA", "nation_count": 5}]}


def test_computed_field():
    sch = schema(
        fields=lambda: {
            "message": compute(
                scalar.String, lambda parent, info, params: "Hello!"
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            message
        }
        """,
    ).data
    assert data == {"message": "Hello!"}
    data = execute(
        sch,
        """
        query {
            name: message
        }
        """,
    ).data
    assert data == {"name": "Hello!"}


def test_data_computed_field():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "message": compute(
                scalar.String,
                f=lambda parent, info, params: f"Hello from '{parent}'",
            ),
        },
    )
    sch = schema(fields=lambda: {"region": query(q.region, region)})
    data = execute(
        sch,
        """
        query {
            region {
                message
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"message": "Hello from 'AFRICA'"},
            {"message": "Hello from 'AMERICA'"},
            {"message": "Hello from 'ASIA'"},
            {"message": "Hello from 'EUROPE'"},
            {"message": "Hello from ''MIDDLE EAST''"},
        ]
    }


def test_computed_arg_simple():
    def get_message(parent, info, params):
        name = params.get("name", "Mr.None")
        return f"Hello, {name}!"

    sch = schema(
        fields=lambda: {
            "message": compute(
                scalar.String,
                get_message,
                params=[argument("name", scalar.String)],
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            message
        }
        """,
    ).data
    assert data == {"message": "Hello, Mr.None!"}

    data = execute(
        sch,
        """
        query {
            message(name: "John")
        }
        """,
    ).data
    assert data == {"message": "Hello, John!"}


def test_computed_arg_nonnull():
    def get_message(parent, info, params):
        name = params["name"]
        return f"Hello, {name}!"

    sch = schema(
        fields=lambda: {
            "message": compute(
                scalar.String,
                get_message,
                params=[argument("name", NonNull(scalar.String))],
            )
        }
    )
    res = execute(
        sch,
        """
        query {
            message
        }
        """,
    )
    assert res.invalid

    data = execute(
        sch,
        """
        query {
            message(name: "John")
        }
        """,
    ).data
    assert data == {"message": "Hello, John!"}


def test_computed_arg_default():
    def get_message(parent, info, params):
        name = params["name"]
        return f"Hello, {name}!"

    sch = schema(
        fields=lambda: {
            "message": compute(
                scalar.String,
                get_message,
                params=[argument("name", scalar.String, "Default")],
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            message
        }
        """,
    ).data
    assert data == {"message": "Hello, Default!"}

    data = execute(
        sch,
        """
        query {
            message(name: "John")
        }
        """,
    ).data
    assert data == {"message": "Hello, John!"}


def test_query_filter_of_function():
    @filter_from_function()
    def filter_region(africa_only: scalar.Boolean):
        if africa_only:
            yield q.name == "AFRICA"

    region = Entity("region", fields=lambda: {"name": query(q.name)})

    sch = schema(
        fields=lambda: {
            "region": query(q.region, region, filters=[filter_region])
        }
    )
    data = execute(
        sch,
        """
        query {
            region {
                name
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }
    data = execute(
        sch,
        """
        query {
            region(africa_only: false) {
                name
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }
    data = execute(
        sch,
        """
        query {
            region(africa_only: true) {
                name
            }
        }
        """,
    ).data
    assert data == {"region": [{"name": "AFRICA"}]}
    data = execute(
        sch,
        """
        query Regions($africa_only: Boolean!) {
            region(africa_only: $africa_only) {
                name
            }
        }
        """,
        variables={"africa_only": True},
    ).data
    assert data == {"region": [{"name": "AFRICA"}]}


def test_query_filter_of_function_arg():
    @filter_from_function()
    def filter_region(enabled: argument("africa_only", scalar.Boolean)):
        if enabled:
            yield q.name == "AFRICA"

    region = Entity("region", fields=lambda: {"name": query(q.name)})

    sch = schema(
        fields=lambda: {
            "region": query(q.region, region, filters=[filter_region])
        }
    )
    data = execute(
        sch,
        """
        query {
            region(africa_only: true) {
                name
            }
        }
        """,
    ).data
    assert data == {"region": [{"name": "AFRICA"}]}


def test_query_filter_of_query():
    region = Entity("region", fields=lambda: {"name": query(q.name)})

    sch = schema(
        fields=lambda: {
            "region": query(
                q.region,
                region,
                filters=[q.name == argument("name", scalar.String)],
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            region {
                name
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }
    data = execute(
        sch,
        """
        query {
            region(name: "AFRICA") {
                name
            }
        }
        """,
    ).data
    assert data == {"region": [{"name": "AFRICA"}]}
    data = execute(
        sch,
        """
        query Regions($name: String) {
            region(name: $name) {
                name
            }
        }
        """,
        variables={"name": "AFRICA"},
    ).data
    assert data == {"region": [{"name": "AFRICA"}]}


def test_query_fragment():
    sch = get_simple_schema()
    data = execute(
        sch,
        """
        fragment common on Region {
            name
        }
        query {
            region { ...common }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }


def test_query_inline_fragment():
    sch = get_simple_schema()
    data = execute(
        sch,
        """
        fragment common on Region {
            name
        }
        query {
            region {
                ...on Region {
                    name
                }
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }


def test_introspection_typename():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    sch = schema(fields=lambda: {"region": query(q.region, region)})
    data = execute(
        sch,
        """
        query {
            region {
                __typename
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"__typename": "region"},
            {"__typename": "region"},
            {"__typename": "region"},
            {"__typename": "region"},
            {"__typename": "region"},
        ]
    }


def test_introspection_graphiql():
    """ Test query which is performed by GraphiQL tool."""
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    sch = schema(fields=lambda: {"region": query(q.region, region)})
    res = execute(
        sch,
        """
        query IntrospectionQuery {
            __schema {
                queryType { name }
                mutationType { name }
                types {
                    ...FullType
                }
                directives {
                    name
                    description
                    locations
                    args {
                        ...InputValue
                    }
                }
            }
        }

        fragment FullType on __Type {
            kind
            name
            description
            fields(includeDeprecated: true) {
                name
                description
                args {
                    ...InputValue
                }
                type {
                    ...TypeRef
                }
                isDeprecated
                deprecationReason
            }
            inputFields {
                ...InputValue
            }
            interfaces {
                ...TypeRef
            }
            enumValues(includeDeprecated: true) {
                name
                description
                isDeprecated
                deprecationReason
            }
            possibleTypes {
                ...TypeRef
            }
        }

        fragment InputValue on __InputValue {
            name
            description
            type { ...TypeRef }
            defaultValue
        }

        fragment TypeRef on __Type {
            kind
            name
            ofType {
                kind
                name
                ofType {
                    kind
                    name
                    ofType {
                        kind
                        name
                        ofType {
                            kind
                            name
                            ofType {
                                kind
                                name
                                ofType {
                                    kind
                                    name
                                    ofType {
                                        kind
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """,
    )
    assert not res.invalid


def test_scalar_json():
    sch = schema(
        fields=lambda: {
            "settings": compute(
                scalar.JSON, f=lambda parent, info, params: {"a": "b"}
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            settings
        }
        """,
    ).data
    assert data == {"settings": {"a": "b"}}


def test_scalar_date():
    import datetime

    sch = schema(
        fields=lambda: {
            "nextday": compute(
                scalar.Date,
                f=lambda parent, info, params: params["date"]
                + datetime.timedelta(1),
                params=[argument("date", NonNull(scalar.Date))],
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            nextday(date: "1987-05-08")
        }
        """,
    ).data
    assert data == {"nextday": "1987-05-09"}


def test_scalar_datetime():
    import datetime

    def nextday(parent, info, params):
        return params["date"] + datetime.timedelta(1)

    sch = schema(
        fields=lambda: {
            "nextday": compute(
                scalar.Datetime,
                f=nextday,
                params=[argument("date", NonNull(scalar.Datetime))],
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            nextday(date: "1987-05-08T12:13:14")
        }
        """,
    ).data
    assert data == {"nextday": "1987-05-09T12:13:14"}


def test_enum():
    day = Enum(
        name="day",
        values=[
            EnumValue(name="sun"),
            EnumValue(name="mon", deprecation_reason="Cancelled"),
            EnumValue(name="tue"),
            EnumValue(name="wed"),
            EnumValue(name="thu"),
            EnumValue(name="fri", description="Friday!"),
        ],
        description="Days of the week, not really",
    )
    sch = schema(
        fields=lambda: {
            "sameday": compute(
                type=day,
                f=lambda parent, info, params: params["day"],
                params=[argument("day", NonNull(day))],
            )
        }
    )
    assert execute(sch, "{sameday(day: sun)}").data == {"sameday": "sun"}
    # XXX(andreypopp): this is for backward compat: we allow string literals as
    # well.
    assert execute(sch, '{sameday(day: "sun")}').data == {"sameday": "sun"}


def test_entity_id():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "nation_list": query(q.nation, nation),
        },
    )
    nation = Entity("nation", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "region": query(q.region, region),
            "first_region_id": query(
                q.region.first().id, type=entity_id.region
            ),
        }
    )
    assert execute(sch, "query { region { id } }").data == {
        "region": [
            {"id": "AFRICA"},
            {"id": "AMERICA"},
            {"id": "ASIA"},
            {"id": "EUROPE"},
            {"id": "'MIDDLE EAST'"},
        ]
    }
    assert execute(sch, "query { region { nation_list { id } } }").data == {
        "region": [
            {
                "nation_list": [
                    {"id": "ALGERIA"},
                    {"id": "ETHIOPIA"},
                    {"id": "KENYA"},
                    {"id": "MOROCCO"},
                    {"id": "MOZAMBIQUE"},
                ]
            },
            {
                "nation_list": [
                    {"id": "ARGENTINA"},
                    {"id": "BRAZIL"},
                    {"id": "CANADA"},
                    {"id": "PERU"},
                    {"id": "'UNITED STATES'"},
                ]
            },
            {
                "nation_list": [
                    {"id": "CHINA"},
                    {"id": "INDIA"},
                    {"id": "INDONESIA"},
                    {"id": "JAPAN"},
                    {"id": "VIETNAM"},
                ]
            },
            {
                "nation_list": [
                    {"id": "FRANCE"},
                    {"id": "GERMANY"},
                    {"id": "ROMANIA"},
                    {"id": "RUSSIA"},
                    {"id": "'UNITED KINGDOM'"},
                ]
            },
            {
                "nation_list": [
                    {"id": "EGYPT"},
                    {"id": "IRAN"},
                    {"id": "IRAQ"},
                    {"id": "JORDAN"},
                    {"id": "'SAUDI ARABIA'"},
                ]
            },
        ]
    }
    assert execute(sch, "query { first_region_id }").data == {
        "first_region_id": "AFRICA"
    }


def test_query_arg_simple():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "region": query(
                query=q.region.filter(
                    q.name == argument("region", scalar.String)
                ),
                type=region,
            )
        }
    )

    res = execute(sch, "query { region { name } }")
    assert res.invalid

    assert execute(
        sch, 'query { region(region: "AFRICA") { name } }'
    ).data == {"region": [{"name": "AFRICA"}]}


def test_query_arg_first():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    # Define schema with `regionByName` field configured to query a region type
    # with specified filter which depends on an argument of the specified type.
    #
    # The value for the argument is going to be supplied by the corresponding
    # GraphQL argument (which are configured automatically).
    sch = schema(
        fields=lambda: {
            "regionByName": query(
                q.region.filter(
                    q.name == argument("region", scalar.String)
                ).first(),
                type=region,
            )
        }
    )

    # Arguments specified in the query are required, so we see a `GraphQLError`
    # raised if we don't supply it.
    res = execute(sch, "query { regionByName { name } }")
    assert res.invalid

    # Now let's supply an argument and see it's being applied.
    assert execute(
        sch, 'query { regionByName(region: "AFRICA") { name } }'
    ).data == {"regionByName": {"name": "AFRICA"}}

    # Now let's supply an argument and see it's being applied.
    assert execute(
        sch, 'query { regionByName(region: "UNKNOWN") { name } }'
    ).data == {"regionByName": None}


def test_err_query_extra_arg():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    sch = schema(fields=lambda: {"region": query(query=q.region, type=region)})
    res = execute(sch, "query { region { name } }", variables={"count": "12"})
    assert res.invalid
    assert res.errors[0].message == 'Unexpected variables: "count"'


def test_err_query_arg_type_mismatch():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    count = argument("count", NonNull(scalar.Int))
    sch = schema(
        fields=lambda: {
            "region": query(
                query=q.region.filter(q.nation.count() == count), type=region
            )
        }
    )

    res = execute(
        sch,
        "query Q($count: Int) { region(count: $count) { name } }",
        variables={"count": None},
    )
    assert res.invalid
    assert (
        res.errors[0].message
        == 'Argument "count : Int!" (supplied by "$count" variable) was not provided. At Root.region.'
    )

    res = execute(
        sch,
        "query Q($count: String) { region(count: $count) { name } }",
        variables={"count": "oops"},
    )
    assert res.invalid
    assert res.errors[0].message == (
        'Variable "$count : String" is attempted to be used as a value of incompatible type "Int!".'
        " At Root.region."
    )


def test_query_related_arg_first():
    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name),
            "nationByName": query(
                q.nation.filter(
                    q.name == argument("name", scalar.String)
                ).first(),
                type=nation,
            ),
        },
    )
    nation = Entity("nation", fields=lambda: {"name": query(q.name)})
    sch = schema(fields=lambda: {"region": query(q.region, type=region)})

    assert (
        execute(
            sch,
            """
            query {
                region {
                    name
                    nationByName(name: "EGYPT") {
                        name
                    }
                }
            }
            """,
        ).data
        == {
            "region": [
                {"name": "AFRICA", "nationByName": None},
                {"name": "AMERICA", "nationByName": None},
                {"name": "ASIA", "nationByName": None},
                {"name": "EUROPE", "nationByName": None},
                {"name": "MIDDLE EAST", "nationByName": {"name": "EGYPT"}},
            ]
        }
    )

    assert (
        execute(
            sch,
            """
            query {
                region {
                    name
                    nationByName(name: "UNKNOWN") {
                        name
                    }
                }
            }
            """,
        ).data
        == {
            "region": [
                {"name": "AFRICA", "nationByName": None},
                {"name": "AMERICA", "nationByName": None},
                {"name": "ASIA", "nationByName": None},
                {"name": "EUROPE", "nationByName": None},
                {"name": "MIDDLE EAST", "nationByName": None},
            ]
        }
    )


def test_query_on_object():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    region_api = Object(
        "region_api",
        fields=lambda: {
            "all": query(q.region, type=region),
            "get": query(
                q.region.filter(
                    q.name == argument("name", scalar.String)
                ).first(),
                type=region,
            ),
        },
    )
    sch = schema(
        fields=lambda: {
            "region": compute(
                type=region_api, f=lambda parent, info, params: {}
            )
        }
    )
    assert (
        execute(
            sch,
            """
            query {
                region {
                    all {
                        name
                    }
                    africa: get(name: "AFRICA") {
                        name
                    }
                }
            }
            """,
        ).data
        == {
            "region": {
                "africa": {"name": "AFRICA"},
                "all": [
                    {"name": "AFRICA"},
                    {"name": "AMERICA"},
                    {"name": "ASIA"},
                    {"name": "EUROPE"},
                    {"name": "MIDDLE EAST"},
                ],
            }
        }
    )


def test_query_arg_scalars():
    schema_for = lambda type: schema(
        fields=lambda: {"value": query(argument("val", type))}
    )
    assert execute(
        schema_for(scalar.String), 'query { value(val: "hey") }'
    ).data == {"value": "hey"}
    assert execute(
        schema_for(scalar.Int), "query { value(val: 42) }"
    ).data == {"value": 42}
    assert execute(
        schema_for(scalar.Float), "query { value(val: 42.2) }"
    ).data == {"value": 42.2}
    assert execute(
        schema_for(scalar.Boolean), "query { value(val: true) }"
    ).data == {"value": True}
    assert execute(
        schema_for(scalar.Date), 'query { value(val: "2012-12-11") }'
    ).data == {"value": "2012-12-11"}
    assert execute(
        schema_for(scalar.Datetime),
        'query { value(val: "2012-12-11T11:12:13") }',
    ).data == {"value": "2012-12-11T11:12:13"}
    assert execute(
        schema_for(scalar.Decimal), 'query { value(val: "12.1314") }'
    ).data == {"value": "12.1314"}
    assert execute(
        schema_for(scalar.ID), 'query { value(val: "some-id") }'
    ).data == {"value": "some-id"}
    # JSON is not supported as query argument at the moment
    with pytest.raises(Error):
        schema_for(scalar.JSON)


def test_exec_err_unknown_field_error():
    sch = get_simple_schema()
    res = execute(
        sch,
        """
        query {
            unknown
        }
        """,
    )
    assert res.invalid


def test_exec_err_query_unknown_arg():
    region = Entity(name="region", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "region": query(
                q.region,
                region,
                filters=[q.name == argument("name", scalar.String)],
            )
        }
    )
    res = execute(
        sch,
        """
        query {
            region(some: 1) { name }
        }
        """,
    )
    assert res.invalid
    assert (
        res.errors[0].message
        == 'The following arguments: "some" are not allowed for this field'
    )


def test_exec_err_compute_unknown_arg():
    @compute_from_function()
    def add(x: scalar.Int, y: scalar.Int) -> scalar.Int:
        return x + y

    sch = schema(fields=lambda: {"add": add})

    res = execute(
        sch,
        """
        query {
            add(x: 1, y: 2, z: 4)
        }
        """,
    )
    assert res.invalid
    assert (
        res.errors[0].message
        == 'The following arguments: "z" are not allowed for this field'
    )


def test_exec_err_compute_null_for_non_null():
    @compute_from_function()
    def number() -> NonNull(scalar.Int):
        return None

    sch = schema(fields=lambda: {"number": number})

    res = execute(
        sch,
        """
        query {
            number
        }
        """,
    )
    assert res.invalid
    assert (
        res.errors[0].message
        == "Cannot return null for non-nullable field Root.number"
    )


def test_exec_err_compute_raises():
    @compute_from_function()
    def number() -> NonNull(scalar.Int):
        raise TypeError("just some error here")

    sch = schema(fields=lambda: {"number": number})

    res = execute(
        sch,
        """
        query {
            number
        }
        """,
    )
    assert res.invalid
    assert res.errors[0].message == "Error while executing Root.number"


def test_conf_err_unknown_field_via_second_path():
    with pytest.raises(Error):
        part = Entity(
            name="part",
            fields=lambda: {"name": query(q.name), "type": query(q.type)},
        )
        schema(
            fields=lambda: {
                "part": query(q.part, type=part),
                "region": query(q.region, type=part),
            }
        )


def test_query_record():
    named = Record(name="named", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "region": query(q.region, named),
            "nation": query(q.nation, named),
        }
    )
    data = execute(
        sch,
        """
        query {
            region { name }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }


def test_query_group():
    # We are going to use Record as the result of this is not a table but a
    # select.
    region_stat = Record(
        name="region_stat",
        fields=lambda: {
            "region_name": query(q.region_name),
            "nation_count": query(q.nation_count),
        },
    )
    sch = schema(
        fields=lambda: {
            "region_stat": query(
                query=(
                    q.nation.group(region_name=q.region.name).select(
                        region_name=q.region_name,
                        nation_count=q.nation.count(),
                    )
                ),
                type=region_stat,
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            region_stat {
                region_name
                nation_count
            }
        }
        """,
    ).data
    assert data == {
        "region_stat": [
            {"nation_count": 5, "region_name": "AFRICA"},
            {"nation_count": 5, "region_name": "AMERICA"},
            {"nation_count": 5, "region_name": "ASIA"},
            {"nation_count": 5, "region_name": "EUROPE"},
            {"nation_count": 5, "region_name": "MIDDLE EAST"},
        ]
    }


def test_query_record_select():
    expect = {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }

    named = Record(
        name="named", fields=lambda: {"display_name": query(q.display_name)}
    )
    sch = schema(
        fields=lambda: {
            "region": query(q.region.select(display_name=q.name), named),
            "nation": query(q.nation.select(display_name=q.name), named),
        }
    )
    assert (
        execute(
            sch,
            """
        query {
            region { name: display_name }
        }
        """,
        ).data
        == expect
    )


def test_query_record_define():
    expect = {
        "region": [
            {"name": "AFRICA"},
            {"name": "AMERICA"},
            {"name": "ASIA"},
            {"name": "EUROPE"},
            {"name": "MIDDLE EAST"},
        ]
    }

    named = Record(
        name="named", fields=lambda: {"display_name": query(q.display_name)}
    )
    sch = schema(
        fields=lambda: {
            "region": query(q.region.define(display_name=q.name), named),
            "nation": query(q.nation.define(display_name=q.name), named),
        }
    )
    assert (
        execute(
            sch,
            """
        query {
            region { name: display_name }
        }
        """,
        ).data
        == expect
    )


def test_err_query_record_define_missing():
    named = Record(
        name="named", fields=lambda: {"display_name": query(q.display_name)}
    )
    with pytest.raises(Error):
        schema(
            fields=lambda: {
                "region": query(q.region.define(display_name=q.name), named),
                "nation": query(q.nation, named),
            }
        )


def test_err_query_record_select_missing():
    named = Record(
        name="named", fields=lambda: {"display_name": query(q.display_name)}
    )
    with pytest.raises(Error):
        schema(
            fields=lambda: {
                "region": query(q.region.select(display_name=q.name), named),
                "nation": query(q.nation, named),
            }
        )


def test_query_connect():
    region = Entity(
        name="region",
        fields=lambda: {"name": query(q.name), "nation": connect(nation)},
    )
    nation = Entity(name="nation", fields=lambda: {"name": query(q.name)})

    sch = schema(
        fields=lambda: {
            "region": connect(
                region,
                filters=[q.name == argument("name", type=scalar.String)],
            ),
            "nation": connect(nation),
        }
    )

    data = execute(
        sch,
        """
        query {
            region {
                count
                africa: get(id: "AFRICA") {
                    name
                }
                none: get_many(id: []) { name }
                africa_only: get_many(id: ["AFRICA"]) { name }
                africa_and_america: get_many(id: ["AFRICA", "AMERICA"]) { name }
                firstTwo: paginated(limit: 2) {
                    name
                }
                all {
                    name
                    nation {
                        count
                    }
                }
            }
        }
        """,
    ).data
    assert data == {
        "region": {
            "count": 5,
            "africa": {"name": "AFRICA"},
            "none": [],
            "africa_only": [{"name": "AFRICA"}],
            "africa_and_america": [{"name": "AFRICA"}, {"name": "AMERICA"}],
            "firstTwo": [{"name": "AFRICA"}, {"name": "AMERICA"}],
            "all": [
                {"name": "AFRICA", "nation": {"count": 5}},
                {"name": "AMERICA", "nation": {"count": 5}},
                {"name": "ASIA", "nation": {"count": 5}},
                {"name": "EUROPE", "nation": {"count": 5}},
                {"name": "MIDDLE EAST", "nation": {"count": 5}},
            ],
        }
    }

    # Let's test with a filter on all/paginated
    data = execute(
        sch,
        """
        query {
            region {
                paginated(name: "AFRICA", limit: 2) { name }
                all(name: "AFRICA") { name }
            }
        }
        """,
    ).data
    assert data == {
        "region": {
            "paginated": [{"name": "AFRICA"}],
            "all": [{"name": "AFRICA"}],
        }
    }


def test_query_connect_filters():
    @filter_from_function()
    def filter_by_name(name: scalar.String = None):
        if name is not None:
            yield q.name.matches(name)

    region = Entity(name="region", fields=lambda: {"name": query(q.name)})

    sch = schema(
        fields=lambda: {"region": connect(region, filters=[filter_by_name])}
    )

    data = execute(
        sch,
        """
        query {
            region {
                count(name: "ICA")
                firstOne: paginated(limit: 1, name: "ICA") { name }
                all(name: "ICA") { name }
            }
        }
        """,
    ).data
    assert data == {
        "region": {
            "count": 2,
            "firstOne": [{"name": "AFRICA"}],
            "all": [{"name": "AFRICA"}, {"name": "AMERICA"}],
        }
    }


def test_query_param():
    current_region = param(
        name="current_region",
        type=scalar.String,
        f=lambda parent, ctx: ctx["region"],
    )
    nation = Entity(name="nation", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "nation": query(
                q.nation.filter(q.region.name == current_region), type=nation
            )
        }
    )
    data = execute(
        sch,
        """
        query {
            nation {
                name
            }
        }
        """,
        context={"region": "ASIA"},
    ).data
    assert data == {
        "nation": [
            {"name": "CHINA"},
            {"name": "INDIA"},
            {"name": "INDONESIA"},
            {"name": "JAPAN"},
            {"name": "VIETNAM"},
        ]
    }
    data = execute(
        sch,
        """
        query {
            nation {
                name
            }
        }
        """,
        context={"region": "EUROPE"},
    ).data
    assert data == {
        "nation": [
            {"name": "FRANCE"},
            {"name": "GERMANY"},
            {"name": "ROMANIA"},
            {"name": "RUSSIA"},
            {"name": "UNITED KINGDOM"},
        ]
    }


def test_err_query_param_invalid_type():
    num_nations = param(
        name="current_region", type=scalar.Int, f=lambda parent, ctx: "oops"
    )
    region = Entity(name="region", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "region": query(
                q.region.filter(q.nation.count() == num_nations), type=region
            )
        }
    )
    res = execute(
        sch,
        """
        query {
            region {
                name
            }
        }
        """,
    )
    assert res.invalid


def test_mutation_simple():
    counter = 0

    @mutation_from_function()
    def increment(v: scalar.Int) -> scalar.Int:
        nonlocal counter
        counter = counter + v
        return counter

    sch = schema(fields=lambda: {}, mutations=[increment])
    data = execute(sch, "mutation { increment(v: 10) }").data
    assert data == {"increment": 10}
    assert counter == 10


@mutation_from_function()
def make_region(name: scalar.String) -> scalar.String:
    db = get_db()
    db.produce("/insert(region := {name := $name})", name=name)
    return name


def find_region(name):
    db = get_db()
    pr = db.produce("top(region?name=$name)", name=name)
    return pr.data


def test_mutation_db_ok():
    sch = schema(fields=lambda: {}, mutations=[make_region])
    db = get_db()
    with db, db.transaction() as tx:
        try:
            # this mutation creates a record in a database
            execute(sch, 'mutation { make_region(name: "NEW") }').data
            # let's see if it's done its work
            assert find_region("NEW")
        finally:
            tx.rollback()


def test_mutation_query_result():
    counter = 0

    RegionWithCounter = Record(
        name="RegionWithCounter",
        fields=lambda: {"name": query(q.name), "counter": query(q.counter)},
    )

    counter_param = param(
        name="counter",
        type=scalar.Int,
        f=lambda parent, ctx: parent["counter"],
    )

    IncrementResult = Object(
        name="IncrementResult",
        fields=lambda: {
            "region": query(
                q.region.select(name=q.name, counter=counter_param),
                type=RegionWithCounter,
            )
        },
    )

    @mutation_from_function()
    def increment(v: scalar.Int) -> IncrementResult:
        nonlocal counter
        counter = counter + v
        return {"counter": counter}

    sch = schema(fields=lambda: {}, mutations=[increment])
    data = execute(
        sch,
        """
        mutation {
            increment(v: 10) {
                region { name, counter }
            }
        }
        """,
    ).data
    assert data == {
        "increment": {
            "region": [
                {"name": "AFRICA", "counter": 10},
                {"name": "AMERICA", "counter": 10},
                {"name": "ASIA", "counter": 10},
                {"name": "EUROPE", "counter": 10},
                {"name": "MIDDLE EAST", "counter": 10},
            ]
        }
    }
    assert counter == 10


def test_arg_input_object():
    getindex = lambda name: lambda parent, info, params: parent.get(name)

    Pos = Object(
        name="Pos",
        fields=lambda: {
            "r": compute(scalar.Int, f=getindex("r")),
            "n": compute(scalar.Int, f=getindex("n")),
            "rd": compute(scalar.Int, f=getindex("rd")),
            "nd": compute(scalar.Int, f=getindex("nd")),
        },
    )

    # InputObject type with variety of fields
    InputPos = InputObject(
        name="InputPos",
        fields=lambda: {
            "r": InputObjectField(scalar.Int),
            "n": InputObjectField(NonNull(scalar.Int)),
            "rd": InputObjectField(scalar.Int, default_value=1),
            "nd": InputObjectField(NonNull(scalar.Int), default_value=2),
        },
    )

    @compute_from_function()
    def get_pos(pos: InputPos) -> Pos:
        return pos

    sch = schema(fields=lambda: {"pos": get_pos})

    data = execute(
        sch,
        """
        query {
            pos(pos: {r: 42, n: 43, rd: 44, nd: 45}) {
                r n rd nd
            }
        }
        """,
    ).data
    assert data == {"pos": {"r": 42, "n": 43, "rd": 44, "nd": 45}}

    # Suppling just a non null field without default value
    data = execute(
        sch,
        """
        query {
            pos(pos: {n: 42}) {
                r n rd nd
            }
        }
        """,
    ).data
    assert data == {"pos": {"r": None, "n": 42, "rd": 1, "nd": 2}}

    # Missing non null field with no default value
    res = execute(
        sch,
        """
        query {
            pos(pos: {r: 42}) {
                r n rd nd
            }
        }
        """,
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        ['Argument "pos : InputPos!":', 'Missing field "InputPos.n"']
    )

    # Now via variables
    data = execute(
        sch,
        """
        query Query($n: Int) {
            pos(pos: {n: $n}) {
                r n rd nd
            }
        }
        """,
        variables={"n": 50},
    ).data
    assert data == {"pos": {"r": None, "n": 50, "rd": 1, "nd": 2}}

    # Now via variables (default value)
    data = execute(
        sch,
        """
        query Query($n: Int = 40) {
            pos(pos: {n: $n}) {
                r n rd nd
            }
        }
        """,
    ).data
    assert data == {"pos": {"r": None, "n": 40, "rd": 1, "nd": 2}}

    # vars: just a non null field with no default
    data = execute(
        sch,
        """
        query Query($pos: InputPos!) {
            pos(pos: $pos) {
                r n rd nd
            }
        }
        """,
        variables={"pos": {"n": 30}},
    ).data
    assert data == {"pos": {"r": None, "n": 30, "rd": 1, "nd": 2}}

    # vars: explicit null
    data = execute(
        sch,
        """
        query Query($pos: InputPos!) {
            pos(pos: $pos) {
                r n rd nd
            }
        }
        """,
        variables={"pos": {"n": 30, "r": None}},
    ).data
    assert data == {"pos": {"r": None, "n": 30, "rd": 1, "nd": 2}}

    # vars: all fields
    data = execute(
        sch,
        """
        query Query($pos: InputPos!) {
            pos(pos: $pos) {
                r n rd nd
            }
        }
        """,
        variables={"pos": {"r": 40, "n": 30, "rd": 50, "nd": 60}},
    ).data
    assert data == {"pos": {"r": 40, "n": 30, "rd": 50, "nd": 60}}

    # vars: missing value for non null
    res = execute(
        sch,
        """
        query Query($pos: InputPos!) {
            pos(pos: $pos) {
                r n rd nd
            }
        }
        """,
        variables={"pos": {"r": 40}},
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        [
            'Variable "$pos : InputPos!" got invalid value:',
            'Field "InputPos.n": missing value',
        ]
    )

    # vars: explicit null for non null
    res = execute(
        sch,
        """
        query Query($pos: InputPos!) {
            pos(pos: $pos) {
                r n rd nd
            }
        }
        """,
        variables={"pos": {"n": None}},
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        [
            'Variable "$pos : InputPos!" got invalid value:',
            'Field "InputPos.n": value could not be null',
        ]
    )

    # vars: explicit null for non null with default
    res = execute(
        sch,
        """
        query Query($pos: InputPos!) {
            pos(pos: $pos) {
                r n rd nd
            }
        }
        """,
        variables={"pos": {"n": 40, "nd": None}},
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        [
            'Variable "$pos : InputPos!" got invalid value:',
            'Field "InputPos.nd": value could not be null',
        ]
    )


def test_arg_list():
    @compute_from_function()
    def addone(nums: List(scalar.Int)) -> List(scalar.Int):
        return [n + 1 for n in nums]

    sch = schema(fields=lambda: {"addone": addone})

    # Basic case
    data = execute(
        sch,
        """
        query {
            addone(nums: [1, 2])
        }
        """,
    ).data
    assert data == {"addone": [2, 3]}

    # Coerce single element to a one-element list
    data = execute(
        sch,
        """
        query {
            addone(nums: 42)
        }
        """,
    ).data
    assert data == {"addone": [43]}

    # Coerce single element to a one-element list
    data = execute(
        sch,
        """
        query {
            addone(nums: 42)
        }
        """,
    ).data
    assert data == {"addone": [43]}

    # Error: wrong element type
    res = execute(
        sch,
        """
        query {
            addone(nums: ["oops"])
        }
        """,
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        ['Argument "nums : [Int]!":', '- At index 0: Expected "Int".']
    )

    # vars: basic
    data = execute(
        sch,
        """
        query Query($nums: [Int]!) {
            addone(nums: $nums)
        }
        """,
        variables={"nums": [1, 2]},
    ).data
    assert data == {"addone": [2, 3]}

    # vars: via default
    data = execute(
        sch,
        """
        query Query($nums: [Int]! = [2, 3]) {
            addone(nums: $nums)
        }
        """,
    ).data
    assert data == {"addone": [3, 4]}

    # vars: override default
    data = execute(
        sch,
        """
        query Query($nums: [Int]! = [2, 3]) {
            addone(nums: $nums)
        }
        """,
        variables={"nums": [1, 2]},
    ).data
    assert data == {"addone": [2, 3]}

    # vars: override default
    data = execute(
        sch,
        """
        query Query($nums: [Int]! = [2, 3]) {
            addone(nums: $nums)
        }
        """,
        variables={"nums": [1, 2]},
    ).data
    assert data == {"addone": [2, 3]}

    # Error: wrong var value
    res = execute(
        sch,
        """
        query Query($nums: [Int]!) {
            addone(nums: $nums)
        }
        """,
        variables={"nums": ["oops"]},
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        [
            'Variable "$nums : [Int]!" got invalid value:',
            '- At index 0: Expected "Int".',
        ]
    )

    # Error: wrong var default value
    res = execute(
        sch,
        """
        query Query($nums: [Int]! = ["oops"]) {
            addone(nums: $nums)
        }
        """,
    )
    assert res.invalid
    assert res.errors[0].message == "\n".join(
        [
            'Variable "$nums : [Int]!" has invalid default value:',
            '- At index 0: Expected "Int".',
        ]
    )


def test_scalar_type_id():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    region_id = entity_id.region
    lineitem = Entity("lineitem", fields=lambda: {})
    lineitem_id = entity_id.lineitem
    partsupp = Entity("partsupp", fields=lambda: {})
    partsupp_id = entity_id.partsupp
    sch = schema(
        fields=lambda: {
            "region": query(
                q.region.filter(q.id == argument("id", region_id)).first(),
                type=region,
            ),
            "lineitem": query(
                q.lineitem.filter(q.id == argument("id", lineitem_id)).first(),
                type=lineitem,
            ),
            "partsupp": query(
                q.partsupp.filter(q.id == argument("id", partsupp_id)).first(),
                type=partsupp,
            ),
        }
    )
    data = execute(
        sch,
        """
        query {
            region(id: "AFRICA") {
                id
                name
            }
        }
        """,
    ).data
    assert data == {"region": {"id": "AFRICA", "name": "AFRICA"}}
    data = execute(
        sch,
        """
        query {
            region(id: "'MIDDLE EAST'") {
                id
                name
            }
        }
        """,
    ).data
    assert data == {"region": {"id": "'MIDDLE EAST'", "name": "MIDDLE EAST"}}
    data = execute(
        sch,
        """
        query {
            lineitem(id: "1.1") {
                id
            }
        }
        """,
    ).data
    assert data == {"lineitem": {"id": "1.1"}}
    data = execute(
        sch,
        """
        query {
            partsupp(id: "'almond aquamarine mint misty red'.'Supplier#000000021'") {
                id
            }
        }
        """,
    ).data
    assert data == {
        "partsupp": {
            "id": "'almond aquamarine mint misty red'.'Supplier#000000021'"
        }
    }


def test_sort():
    region = Entity("region", fields=lambda: {"name": query(q.name)})
    sch = schema(
        fields=lambda: {
            "region": query(q.region, sort=q.name.desc(), type=region)
        }
    )

    data = execute(
        sch,
        """
        query {
            region {
                name
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "MIDDLE EAST"},
            {"name": "EUROPE"},
            {"name": "ASIA"},
            {"name": "AMERICA"},
            {"name": "AFRICA"},
        ]
    }


def test_query_transform_field():
    def emphasis(value):
        return value + "!!!"

    region = Entity(
        "region",
        fields=lambda: {
            "name": query(q.name, type=scalar.String, transform=emphasis)
        },
    )
    sch = schema(fields=lambda: {"region": query(q.region, type=region)})

    data = execute(
        sch,
        """
        query {
            region {
                name
            }
        }
        """,
    ).data
    assert data == {
        "region": [
            {"name": "AFRICA!!!"},
            {"name": "AMERICA!!!"},
            {"name": "ASIA!!!"},
            {"name": "EUROPE!!!"},
            {"name": "MIDDLE EAST!!!"},
        ]
    }


def test_query_transform_at_root():
    def emphasis(value):
        return [v + "!!!" for v in value]

    sch = schema(
        fields=lambda: {
            "region_name": query(
                q.region.name, type=scalar.String, transform=emphasis
            )
        }
    )

    data = execute(
        sch,
        """
        query {
            region_name
        }
        """,
    ).data
    assert data == {
        "region_name": [
            "AFRICA!!!",
            "AMERICA!!!",
            "ASIA!!!",
            "EUROPE!!!",
            "MIDDLE EAST!!!",
        ]
    }


def test_query_keep():
    nation = Entity("nation", fields=lambda: {"name": query(q.name)})
    nation_name = argument("nation_name", type=scalar.String)
    sch = schema(
        fields=lambda: {
            "nation": query(
                q.nation.filter(q.name == nation_name)
                .keep(this_nation=q.here())
                .region.this_nation.first(),
                type=nation,
            ),
            "nation_name": query(
                q.nation.filter(q.name == nation_name)
                .keep(this_nation=q.here())
                .region.nation.filter(q.name == q.this_nation.name)
                .name
            ),
            "nation_name_dup": query(
                q.nation.filter(q.name == nation_name)
                .keep(this_nation=q.here())
                .region.nation.this_nation.name
            ),
        }
    )
    data = execute(
        sch,
        """
        query {
            nation(nation_name: "JAPAN") { name }
            nation_name(nation_name: "JAPAN")
            nation_name_dup(nation_name: "JAPAN")
        }
        """,
    ).data
    assert data == {
        "nation": {"name": "JAPAN"},
        "nation_name": ["JAPAN"],
        "nation_name_dup": ["JAPAN"],
    }


def test_directive_skip_field():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        query($skip: Boolean!) {
            africa {
                name
                nation_count @skip(if: $skip)
            }
        }
        """,
        variables={"skip": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}

    data = execute(
        sch,
        """
        query($skip: Boolean!) {
            africa {
                name
                nation_count @skip(if: $skip)
            }
        }
        """,
        variables={"skip": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}


def test_directive_skip_fragment():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        fragment Stats on region {
            nation_count
        }
        query($skip: Boolean!) {
            africa {
                name
                ...Stats @skip(if: $skip)
            }
        }
        """,
        variables={"skip": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}

    data = execute(
        sch,
        """
        fragment Stats on region {
            nation_count
        }
        query($skip: Boolean!) {
            africa {
                name
                ...Stats @skip(if: $skip)
            }
        }
        """,
        variables={"skip": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}


def test_directive_skip_inline_fragment():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        query($skip: Boolean!) {
            africa {
                name
                ... on region @skip(if: $skip) {
                    nation_count
                }
            }
        }
        """,
        variables={"skip": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}

    data = execute(
        sch,
        """
        query($skip: Boolean!) {
            africa {
                name
                ... on region @skip(if: $skip) {
                    nation_count
                }
            }
        }
        """,
        variables={"skip": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}


def test_directive_include_field():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        query($include: Boolean!) {
            africa {
                name
                nation_count @include(if: $include)
            }
        }
        """,
        variables={"include": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}

    data = execute(
        sch,
        """
        query($include: Boolean!) {
            africa {
                name
                nation_count @include(if: $include)
            }
        }
        """,
        variables={"include": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}


def test_directive_include_fragment():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        fragment Stats on region {
            nation_count
        }
        query($include: Boolean!) {
            africa {
                name
                ...Stats @include(if: $include)
            }
        }
        """,
        variables={"include": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}

    data = execute(
        sch,
        """
        fragment Stats on region {
            nation_count
        }
        query($include: Boolean!) {
            africa {
                name
                ...Stats @include(if: $include)
            }
        }
        """,
        variables={"include": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}


def test_directive_include_inline_fragment():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        query($include: Boolean!) {
            africa {
                name
                ... on region @include(if: $include) {
                    nation_count
                }
            }
        }
        """,
        variables={"include": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}

    data = execute(
        sch,
        """
        query($include: Boolean!) {
            africa {
                name
                ... on region @include(if: $include) {
                    nation_count
                }
            }
        }
        """,
        variables={"include": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}


def test_directive_skip_over_include():
    sch = get_simple_schema()

    data = execute(
        sch,
        """
        query($include: Boolean!, $skip: Boolean!) {
            africa {
                name
                nation_count @include(if: $include) @skip(if: $skip)
            }
        }
        """,
        variables={"include": True, "skip": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}

    data = execute(
        sch,
        """
        query($include: Boolean!, $skip: Boolean!) {
            africa {
                name
                nation_count @include(if: $include) @skip(if: $skip)
            }
        }
        """,
        variables={"include": False, "skip": True},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}

    data = execute(
        sch,
        """
        query($include: Boolean!, $skip: Boolean!) {
            africa {
                name
                nation_count @include(if: $include) @skip(if: $skip)
            }
        }
        """,
        variables={"include": True, "skip": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA", "nation_count": 5}]}

    data = execute(
        sch,
        """
        query($include: Boolean!, $skip: Boolean!) {
            africa {
                name
                nation_count @include(if: $include) @skip(if: $skip)
            }
        }
        """,
        variables={"include": False, "skip": False},
    ).data
    assert data == {"africa": [{"name": "AFRICA"}]}
