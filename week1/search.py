#
# The main search hooks for the Search Flask application.
#
from flask import (
    Blueprint, redirect, render_template, request, url_for
)

from week1.opensearch import get_opensearch

from sys import maxsize

bp = Blueprint('search', __name__, url_prefix='/search')


# Process the filters requested by the user and return a tuple that is appropriate for use in: the query, URLs displaying the filter and the display of the applied filters
# filters -- convert the URL GET structure into an OpenSearch filter query
# display_filters -- return an array of filters that are applied that is appropriate for display
# applied_filters -- return a String that is appropriate for inclusion in a URL as part of a query string.  This is basically the same as the input query string
def process_filters(filters_input):
    # Filters look like: &filter.name=regularPrice&regularPrice.key={{ agg.key }}&regularPrice.from={{ agg.from }}&regularPrice.to={{ agg.to }}
    filters = []
    # Also create the text we will use to display the filters that are applied
    display_filters = []
    applied_filters = ""
    for filter in filters_input:
        type = request.args.get(filter + ".type")
        display_name = request.args.get(filter + ".displayName", filter)
        #
        # We need to capture and return what filters are already applied so they can be automatically added to any existing links we display in aggregations.jinja2
        applied_filters += "&filter.name={}&{}.type={}&{}.displayName={}".format(filter, filter, type, filter,
                                                                                 display_name)
        # TODO: IMPLEMENT AND SET filters, display_filters and applied_filters.
        # filters get used in create_query below.  display_filters gets used by display_filters.jinja2 and applied_filters gets used by aggregations.jinja2 (and any other links that would execute a search.)
        LOWER_BOUND_STR = 'gte'
        UPPER_BOUND_STR = 'lte'
        KEY_STR = '.key'
        TO_STR = '.to'
        FROM_STR = '.from'
        DEFAULT_LOWER = 0
        DEFAULT_UPPER = maxsize

        if type == "range":
            newRangeFilter = {
                "range": {
                    filter: {
                        LOWER_BOUND_STR: request.args.get(
                            filter + FROM_STR) if request.args.get(filter + FROM_STR) else DEFAULT_LOWER
                    }
                }
            }
            newRangeFilter['range'][filter][UPPER_BOUND_STR] = request.args.get(
                filter + TO_STR) if request.args.get(filter + TO_STR) else DEFAULT_UPPER

            _to = newRangeFilter['range'][filter][UPPER_BOUND_STR]
            _from = newRangeFilter['range'][filter][LOWER_BOUND_STR]

            filters.append(newRangeFilter)
            display_filters.append(
                f'Bounding results using {display_name} between {_from} and {_to} inclusive.')
            applied_filters += f"&{filter}.from={_from}&{filter}.to={_to}"
        elif type == "terms":
            newTermFilter = {
                "term": {}
            }
            newTermFilter['term'][filter] = request.args.get(
                filter + KEY_STR, '*')

            _key = newTermFilter['term'][filter]

            filters.append(newTermFilter)
            display_filters.append(
                f'Filtering via {display_name} on term "{_key}".')
            applied_filters += f'&{filter}.key={_key}'

    print("Filters: {}".format(filters))

    return filters, display_filters, applied_filters


# Our main query route.  Accepts POST (via the Search box) and GETs via the clicks on aggregations/facets
@bp.route('/query', methods=['GET', 'POST'])
def query():
    # Load up our OpenSearch client from the opensearch.py file.
    opensearch = get_opensearch()
    # Put in your code to query opensearch.  Set error as appropriate.
    error = None
    user_query = None
    query_obj = None
    display_filters = None
    applied_filters = ""
    filters = None
    sort = "_score"
    sortDir = "desc"
    if request.method == 'POST':  # a query has been submitted
        user_query = request.form['query']
        if not user_query:
            user_query = "*"
        sort = request.form["sort"]
        if not sort:
            sort = "_score"
        sortDir = request.form["sortDir"]
        if not sortDir:
            sortDir = "desc"
        query_obj = create_query(user_query, [], sort, sortDir)
    elif request.method == 'GET':  # Handle the case where there is no query or just loading the page
        user_query = request.args.get("query", "*")
        filters_input = request.args.getlist("filter.name")
        sort = request.args.get("sort", sort)
        sortDir = request.args.get("sortDir", sortDir)
        if filters_input:
            (filters, display_filters, applied_filters) = process_filters(filters_input)

        query_obj = create_query(user_query, filters, sort, sortDir)
    else:
        query_obj = create_query("*", [], sort, sortDir)

    print("query obj: {}".format(query_obj))
    response = opensearch.search(index="bbuy_products", body=query_obj)

    # Postprocess results here if you so desire

    # print(response)
    if error is None:
        return render_template("search_results.jinja2", query=user_query, search_response=response,
                               display_filters=display_filters, applied_filters=applied_filters,
                               sort=sort, sortDir=sortDir)
    else:
        redirect(url_for("index"))


def create_query(user_query, filters, sort="_score", sortDir="desc"):
    print("Query: {} Filters: {} Sort: {}".format(user_query, filters, sort))
    query_obj = {
        "size": 10,
        "sort": {
            sort: sortDir
        },
        "query": {
            "function_score": {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "simple_query_string": {
                                    "fields": ["name^100", "shortDescription^25", "longDescription^10", "department"],
                                    "query": user_query
                                }
                            }
                        ],
                        "filter": filters
                    }
                },
                "boost_mode": "multiply",
                "score_mode": "avg",
                "functions": [
                    {
                        "field_value_factor": {
                            "field": "salesRankShortTerm",
                            "modifier": "reciprocal",
                            "missing": 100000000
                        }
                    },
                    {
                        "field_value_factor": {
                            "field": "salesRankMediumTerm",
                            "modifier": "reciprocal",
                            "missing": 100000000
                        }
                    },
                    {
                        "field_value_factor": {
                            "field": "salesRankLongTerm",
                            "modifier": "reciprocal",
                            "missing": 100000000
                        }
                    }
                ]
            }
        },
        "aggs": {
            "regularPrice": {
                "range": {
                    "field": "regularPrice",
                    "ranges": [
                        {
                            "to": '100',
                            "key": "$"
                        },
                        {
                            "from": '100',
                            "to": '200',
                            "key": "$$"
                        },
                        {
                            "from": '200',
                            "to": '300',
                            "key": "$$$"
                        },
                        {
                            "from": '300',
                            "to": '400',
                            "key": "$$$$"
                        },
                        {
                            "from": '400',
                            "to": '500',
                            "key": "$$$$$"
                        },
                        {
                            "from": '500',
                            "key": "$$$$$$"
                        }
                    ]
                }
            },
            "missing_images": {
                "missing": {
                    "field": "image.keyword"
                }
            },
            "department": {
                "terms": {
                    "field": "department.keyword",
                    "missing": "N/A",
                    "size": 10,
                    "min_doc_count": 0
                }
            }
        }
    }
    return query_obj
