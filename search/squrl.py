"""
squrl.py
This python module enables parsing of requests in SQURL, an SQL URL. It handles the conversion of the SQURL query portion of a URL to an SQL query
Version 0.5
Annette Greiner, NERSC DAS, 5/22/15
========
Suppose your web app receives a request for http://mydomain.com/api/uri_fragment
This module handles a uri_fragment, of the form
mytable/expression/PRED[/expression][/CONJ/expression/PRED[/expression]]
where mytable is the table to query, and expression can be of the form
value[/OP/value]
where value can be the name of a column (mycolumn), a column plus an array index (mycolumn.2), a numeric value, or a simple string.
OP (operation) can be DIV, TIMES, PLUS, or MINUS
CONJ (conjunction) can be AND or OR
PRED (predicate) can be EQ, NEQ, LT, LTE, GT, GTE, LIKE, NOTLIKE, ISNULL, or ISNOTNULL
Parentheses can be used at the beginning or end of a value to control the order of operations.
The mytable parameter can also be shorthand for a complex SQL FROM clause, if the clause is entered into the config_queries dict

e.g.
Candidate/DECAM_FLUX.2/GT/0.631
becomes
SELECT * FROM candidate WHERE DECAM_FLUX[2] > 0.631

Candidate/DECAM_FLUX.2/DIV/DECAM_MW_TRANSMISSION.2/GT/0.631/AND/DECAM_FLUX.4/DIV/DECAM_MW_TRANSMISSION.4/GT/DECAM_FLUX.2/DIV/DECAM_MW_TRANSMISSION.2/TIMES/4.365 
becomes
SELECT * FROM candidate WHERE DECAM_FLUX[2] / DECAM_MW_TRANSMISSION[2] > 0.631 AND DECAM_FLUX[4] / DECAM_MW_TRANSMISSION[4] > DECAM_FLUX[2] / DECAM_MW_TRANSMISSION[2] * 4.365

To use SQURL, you'll need to configure the tables that users can query and the limit on rows returned, below.
"""

import re, sys
import custom_check # uncomment to add your own custom statement check.

# ---------------- Basic configuration -----------------
# in the 'config_queries' dict below, enter the name of each table that you want to allow queries against as a key, 
# then for each table, 
#   enter a from_clause if you want to specify that portion of the SQL in advance (good for complex queries, such as joins).
#   enter fields as a python list of the columns you want to be queriable. 
#   for db tables that contain arrays, list them under the 'arrays' key. For each, enter a dict with column names as keys and max array indices as values.

  # config_queries = {
    # 'animals': { # this can also be a shortcut name for the particular "from" clause you assign rather than a table name
    #     'from_clause': 'select * from animals join owners on animals.id=owners.animal_id', # use '' if you just want a simple query of the table
    #     'fields': [
    #         'id',
    #         'species',
    #         'breed',
    #         'healthparams'
    #     ],
    #     'arrays': {
    #         {
    #         'healthparams': 4
    #         }
    #     }
    # }
    # 'owners': {
    #       ...


config_queries = {
    'default': {
        'from_clause': "candidate left join decam on candidate.id = decam.cand_id left join wise on candidate.id = wise.cand_id",
        'fields': [
            'candidate.id',
            'decam.cand_id',
            'wise.cand_id',
            'brickid',
            'objid',
            'type',
            'ra',
            'dec',
            'uflux',
            'gflux',
            'rflux',
            'iflux',
            'zflux',
            'yflux',
            'uflux_ivar',
            'gflux_ivar',
            'rflux_ivar',
            'iflux_ivar',
            'zflux_ivar',
            'yflux_ivar',
            'u_anymask',
            'g_anymask',
            'r_anymask',
            'i_anymask',
            'z_anymask',
            'y_anymask',
            'w1flux',
            'w2flux',
            'w3flux',
            'w4flux',
        ],
        'arrays': {}
    },
    'candidate': {
        'from_clause': '',
        'fields': [
            'brickid',
            'objid',
            'blob',
            'type',
            'ra',
            'ra_ivar',
            'dec',
            'dec_ivar',
            'bx',
            'by',
            'bx0',
            'by0',
            'ebv',
            'dchisq1',
            'dchisq2',
            'dchisq3',
            'dchisq4',
            'fracdev',
            'fracdev_ivar',
            'shapeexp_r',
            'shapeexp_r_ivar',
            'shapeexp_e1',
            'shapeexp_e1_ivar',
            'shapeexp_e2',
            'shapeexp_e2_ivar',
            'shapeexp_r',
            'shapedev_r_ivar',
            'shapedev_e1',
            'shapedev_e1_ivar',
            'shapedev_e2',
            'shapedev_e2_ivar',
        ],
        'arrays': {}
    },
    'decam': {
        'from_clause': '',
        'fields': [
            'cand_id',
            'uflux',
            'uflux_ivar',
            'ufracflux',
            'ufracmasked',
            'ufracin',
            'u_rchi2',
            'unobs',
            'u_anymask',
            'u_allmask',
            'u_ext',
            'gflux',
            'gflux_ivar',
            'gfracflux',
            'gfracmasked',
            'gfracin',
            'g_rchi2',
            'gnobs',
            'g_anymask',
            'g_allmask',
            'g_ext',
            'rflux',
            'rflux_ivar',
            'rfracflux',
            'rfracmasked',
            'rfracin',
            'r_rchi2',
            'rnobs',
            'r_anymask',
            'r_allmask',
            'r_ext',
            'iflux',
            'iflux_ivar',
            'ifracflux',
            'ifracmasked',
            'ifracin',
            'i_rchi2',
            'inobs',
            'i_anymask',
            'i_allmask',
            'i_ext',
            'zflux',
            'zflux_ivar',
            'zfracflux',
            'zfracmasked',
            'zfracin',
            'z_rchi2',
            'znobs',
            'z_anymask',
            'z_allmask',
            'z_ext',
            'yflux',
            'yflux_ivar',
            'yfracflux',
            'yfracmasked',
            'yfracin',
            'y_rchi2',
            'ynobs',
            'y_anymask',
            'y_allmask',
            'y_ext'
        ],
        'arrays': {}
    },
    'wise': {
        'from_clause': '',
        'fields': [
            'cand_id',
            'w1flux',
            'w1flux_ivar',
            'w1fracflux',
            'w1_rchi2',
            'w1nobs',
            'w1_ext',
            'w2flux',
            'w2flux_ivar',
            'w2fracflux',
            'w2_rchi2',
            'w2nobs',
            'w2_ext',
            'w3flux',
            'w3flux_ivar',
            'w3fracflux',
            'w3_rchi2',
            'w3nobs',
            'w3_ext',
            'w4flux',
            'w4flux_ivar',
            'w4fracflux',
            'w4_rchi2',
            'w4nobs',
            'w4_ext',
        ],
        'arrays': {}
    }
}

# Set the maximum number of rows to return
limit = '100' # use '' if no limit

# -------------- End of basic configuration ----------------


def unsqurl(instring):
    """
    accepts a string that is a fragment of an URL, like "animals/species/EQ/elephant"
    returns a dict of the form
    {"returncode": '200', "error": "Error string if there is an error", "sql": "SELECT ID, SPECIES, BREED, HEALTHPARAMS FROM ...", "table": "requestedtable"}
    """
    result = {"returncode": '200', "error": "", "sql": "", "table": "unknown"}

    try:
        instring = instring.upper()
        badchar = re.search(r'([;\s\"\'@-])', instring)
        if badchar: 
            result['error'] = "Oops, there is a character in the URI that is not allowed: \"" + badchar.group(1) + "\""
            result['returncode'] = "400"
            return result

        tables = []
        columns = []
        arrays = {}
        from_clause = ''
        #determine the table name
        table, squrlstring = instring.upper().split('/', 1)
        for key in config_queries.keys():
            # capitalize table names
            tables.append(key.upper())
            temp = config_queries.pop(key)
            config_queries[key.upper()] = temp
        if table in tables:
            result['table'] = table
            raw_columns = config_queries[table]['fields'] # stopped here. key is not upper case yet.
            # convert column names in config_queries to upper case, store in columns var
            for col in raw_columns:
                columns.append(col.upper())
            # convert table and column names in arrays to upper case, store in arrays var
            array_dict = config_queries[table]['arrays']
            for arraykey in array_dict:
                arrays[arraykey.upper()] = array_dict[arraykey].upper()
            # make a list of columns to include in the query
            col_list = ", ".join(columns)
            if config_queries[table]['from_clause'] != '':
                table_phrase = config_queries[table]['from_clause']
            else:
                table_phrase = table
            result['sql'] = "SELECT " + col_list + " FROM " + table_phrase + " WHERE "
        else:
            result['error'] = "No known table was found in the query."
            result['returncode'] = "400"
            return result
        #break urlstring into statements by conjunction
        statements = []
        conjunctions = []
        splits = re.split(r'(\/AND\/|\/OR\/)', squrlstring)
        if splits == -1:
            statements.append(squrlstring)
        else:
            for i in range (0, len(splits)):
                if i%2 == 0: statements.append(splits[i])
                else: conjunctions.append(splits[i])
        for statement in statements:
            # ------ custom checks ---------
            # Uncomment the lines below to use custom checks. To do so, create a function check_custom(statement) that returns 
            # a dictionary like that in the result variable
            custom_result = custom_check.check_custom(statement)
            if custom_result['returncode'] != '200':
                return custom_result
            elif custom_result['sql'] != '':
                result['sql'] += custom_result['sql']
                # break out of the statement processing
                continue
            # keep checking if custom check didn't find an error but didn't return some sql
            # ------- end custom checks ----------
            # basic checks
            columnpresent = False # check on whether a column name is given in the statement; initially assume no column is mentioned
            stringpresent = False # check on whether string is used with a compatible predicate
            numberpresent = False # check on whether a number is used with a compatible predicate
            #add the conjunction to the SQL query, if there is one
            stindex = statements.index(statement)
            if stindex > 0 and len(conjunctions) >= stindex:
                #switch
                if conjunctions[stindex - 1] == "/AND/":
                    result['sql'] += " AND "
                elif conjunctions[stindex - 1] == "/OR/":
                    result['sql'] += " OR "
            #break statement into expressions by predicate
            expressions = []
            predicates = []
            ssplits = re.split(r'(\/EQ\/|\/NEQ\/|\/LT\/|\/LTE\/|\/GT\/|\/GTE\/|\/LIKE\/|\/NOTLIKE\/|\/ISNULL\/|\/ISNULL|\/ISNOTNULL\/|\/ISNOTNULL)', statement)
            if ssplits == -1:
                expressions.append(statement)
            else:
                for j in range (0, len(ssplits)):
                    if j%2 == 0: expressions.append(ssplits[j])
                    else: predicates.append(ssplits[j])
            for expression in expressions:
                # add the predicate to the SQL query, if there is one
                expindex = expressions.index(expression)
                if expindex > 0 and len(predicates) >= expindex:
                    #switch
                    if predicates[expindex - 1] == "/EQ/":
                        result['sql'] += " = "
                    elif predicates[expindex - 1] == "/NEQ/":
                        result['sql'] += " != "
                    elif predicates[expindex - 1] == "/LT/":
                        result['sql'] += " < "
                    elif predicates[expindex - 1] == "/LTE/":
                        result['sql'] += " <= "
                    elif predicates[expindex - 1] == "/GT/":
                        result['sql'] += " > "
                    elif predicates[expindex - 1] == "/GTE/":
                        result['sql'] += " >= "
                    elif predicates[expindex - 1] == "/LIKE/":
                        result['sql'] += " LIKE "
                    elif predicates[expindex - 1] == "/NOTLIKE/":
                        result['sql'] += " NOT LIKE "
                    elif predicates[expindex - 1] == "/ISNULL/":
                        result['sql'] += " IS NULL"
                    elif predicates[expindex - 1] == "/ISNULL":
                        result['sql'] += " IS NULL"
                    elif predicates[expindex - 1] == "/ISNOTNULL/":
                        result['sql'] += " IS NOT NULL"
                    elif predicates[expindex - 1] == "/ISNOTNULL":
                        result['sql'] += " IS NOT NULL"
                #break expressions into values by operation
                values=[]
                operations=[]
                esplits = re.split(r'(\/DIV\/|\/TIMES\/|\/PLUS\/|\/MINUS\/)', expression)
                if esplits == -1:
                    values.append(expression)
                else:
                    for k in range(0, len(esplits)):
                        if k%2 == 0: values.append(esplits[k])
                        else: operations.append(esplits[k])
                #add the expressions to the SQL query
                for m in range(0, len(values)):
                    if  m > 0 and len(operations) >= m:
                        #switch
                        if operations[m-1] == "/DIV/":
                                result['sql'] += " / "
                        elif operations[m-1] == "/TIMES/":
                                result['sql'] += " * "
                        elif operations[m-1] == "/MINUS/":
                                result['sql'] += " - "
                        elif operations[m-1] == "/PLUS/":
                                result['sql'] += " + "
                    #add the values to the SQL query
                    leftparen = rightparen = ''
                    if values[m].startswith('('):
                        leftparen = '('
                        thevalue = values[m][1:]
                    elif values[m].endswith(')'):
                        rightparen = ')'
                        thevalue = values[m][:-1]
                    else: thevalue = values[m]
                    result['sql'] += leftparen # the empty string if it doesn't start with a paren
                    isempty = re.match(r'', thevalue)
                    isalphanum = re.match(r'([a-zA-Z_][a-zA-Z0-9_\.%]+)$', thevalue) # dot allowed to enable tables in joins
                    hasarray = re.match(r'([a-zA-Z_][a-zA-Z0-9_]+)\.(\d+)$', thevalue)
                    isnumeric = re.match(r'-?[\d\.]+$', thevalue)
                    if hasarray:
                        #a column name plus array index
                        column = hasarray.group(1)
                        index = hasarray.group(2)
                        if column in columns and int(index) <= arrays[table][column]:
                            result['sql'] += column + "[" + index + "]"
                            columnpresent = True
                        else:
                            result['error'] = "Column " + column + " with array index " + index + " not found in the specified table."
                            result['returncode'] = "400"
                            return result
                    elif isalphanum:
                        if thevalue in columns:
                            #a column name
                            if arrays.has_key(table)==False or arrays[table][thevalue] == None:
                                result['sql'] += thevalue
                                columnpresent = True
                            else: 
                                result['error'] = "Column " + thevalue + " requires an array index."
                                result['returncode'] = "400"
                                return result
                        else:
                            #not a column name, treat as a string
                            if expindex > 0 and predicates[expindex-1] not in ['/LIKE/', '/NOTLIKE/']:
                                result['error'] = predicates[expindex-1]  + " must be followed by a numeric value."
                                result['returncode'] = "400"
                                return result
                            else: 
                                result['sql']+="'" + thevalue + "'"
                                stringpresent = True
                    elif isnumeric:
                        #an integer or float
                        if float(thevalue) == 0 and operations[m-1] == "/DIV/": 
                            result['error'] = "Division by zero is not allowed."
                            result['returncode'] = "400"
                            return result
                        else: 
                            result['sql'] += thevalue
                            numberpresent = True
                    elif isempty:
                        # predicate takes no object
                        if predicates[expindex-1] in ['/ISNULL/', '/ISNULL', '/ISNOTNULL/', '/ISNOTNULL']: result['sql']+=''
                        else: 
                            result['error'] = "Got an empty value where there should have been something: near " + predicates[expindex-1]
                            result['returncode'] = "400"
                            return result
                    else:
                        #sadface
                        result['error'] = thevalue + " is not a usable value nor a column in the specified table."
                        result['returncode'] = "400"
                        return result
                    result['sql'] += rightparen # the empty string if no right paren
            # if no column name turned up in the statement
            if columnpresent == False: 
                result['error'] = "Each statement must reference a column in the specified table"
                result['returncode'] = "400"
                return result
            if stringpresent == True and predicates[0] not in ['/LIKE/', '/NOTLIKE/']: 
                result['error'] = "Strings cannot be used with predicates other than LIKE and NOTLIKE."
                result['returncode'] = "400"
                return result
            if numberpresent == True and predicates[0] in ['/LIKE/','/NOTLIKE/']: 
                result['error'] = "Numbers cannot be used with LIKE and NOTLIKE."
                result['returncode'] = "400"
                return result
        if limit != '': result['sql']+=' LIMIT ' + limit + ';'
    except Exception as exc:
        result['returncode'] = '500'
        result['error'] = "An error occurred. Unable to parse the URI string. " + str(type(exc)) + ": " + str(exc)
        return result

    return result
